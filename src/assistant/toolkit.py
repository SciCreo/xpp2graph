"""
Assistant toolkit that orchestrates graph queries and semantic search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from neo4j import GraphDatabase

from src.api.queries import GraphQueryService
from src.config import Neo4jSettings, load_settings
from src.embeddings.client import EmbeddingClient, HashEmbeddingClient
from src.embeddings.store import LocalVectorStore, VectorMatch


@dataclass
class AssistantToolkit:
    settings: Neo4jSettings
    embedding_client: EmbeddingClient
    store: LocalVectorStore

    def __post_init__(self) -> None:
        self._driver = GraphDatabase.driver(
            self.settings.uri,
            auth=(self.settings.username, self.settings.password),
        )
        self._query_service = GraphQueryService(self._driver, database=self.settings.database)

    @classmethod
    def from_defaults(
        cls,
        *,
        store: LocalVectorStore,
        embedding_client: EmbeddingClient | None = None,
        settings: Neo4jSettings | None = None,
    ) -> "AssistantToolkit":
        settings = settings or load_settings()
        embedding_client = embedding_client or HashEmbeddingClient()
        return cls(settings=settings, embedding_client=embedding_client, store=store)

    # Core tools ------------------------------------------------------------------
    def search_nodes(
        self,
        query: str,
        *,
        top_k: int = 5,
        label: str | None = None,
    ) -> List[Dict[str, Any]]:
        embedding = self.embedding_client.embed_documents([query])[0]
        matches = self.store.similarity_search(embedding, top_k=top_k, label=label)
        results: List[Dict[str, Any]] = []
        for match in matches:
            node_props = self._fetch_node_properties(match.node_id)
            results.append(
                {
                    "matchScore": match.score,
                    "node": node_props,
                    "text": match.text,
                    "metadata": match.metadata,
                }
            )
        return results

    def get_neighbors(self, node_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        query = """
        MATCH path = (n {id: $nodeId})-[r*1..$depth]-(neighbor)
        WITH neighbor, length(path) AS hop, [rel IN relationships(path) | type(rel)] AS relTypes
        RETURN neighbor, hop, relTypes
        """
        with self._driver.session(database=self.settings.database) as session:
            records = session.run(query, nodeId=node_id, depth=depth)
            neighbors = []
            for record in records:
                neighbor_node = record["neighbor"]
                neighbors.append(
                    {
                        "id": neighbor_node["id"],
                        "labels": list(neighbor_node.labels),
                        "properties": dict(neighbor_node),
                        "depth": record["hop"],
                        "relationships": record["relTypes"],
                    }
                )
            return neighbors

    def get_method_source(self, method_id: str) -> Dict[str, Any]:
        query = """
        MATCH (m:Method {id: $methodId})
        RETURN m.name AS name, m.className AS className, m.model AS model, m.body AS body
        """
        with self._driver.session(database=self.settings.database) as session:
            record = session.run(query, methodId=method_id).single()
            if not record:
                raise LookupError(f"Method {method_id} not found")
            return {
                "id": method_id,
                "name": record["name"],
                "className": record["className"],
                "model": record["model"],
                "body": record["body"],
            }

    def explain_node(self, node_id: str) -> Dict[str, Any]:
        node_props = self._fetch_node_properties(node_id)
        vector_entry = self.store.fetch(node_id)
        summary = vector_entry.text if vector_entry else None
        return {
            "node": node_props,
            "summary": summary,
            "neighbors": self.get_neighbors(node_id, depth=1),
        }

    def close(self) -> None:
        self._driver.close()
        self.store.close()

    # Internal helpers ------------------------------------------------------------
    def _fetch_node_properties(self, node_id: str) -> Dict[str, Any]:
        query = """
        MATCH (n {id: $nodeId})
        RETURN n AS node, labels(n) AS labels
        """
        with self._driver.session(database=self.settings.database) as session:
            record = session.run(query, nodeId=node_id).single()
            if not record:
                raise LookupError(f"Node {node_id} not found")
            node = record["node"]
            properties = dict(node)
            properties["labels"] = record["labels"]
            return properties


