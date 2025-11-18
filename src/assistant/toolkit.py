"""
Assistant toolkit that orchestrates graph queries and semantic search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import numpy as np
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from src.config import (
    GraphIndexSettings,
    Neo4jSettings,
    OpenAISettings,
    load_index_settings,
    load_openai_settings,
    load_settings,
)
from src.embeddings.client import EmbeddingClient, OpenAIEmbeddingClient


@dataclass
class AssistantToolkit:
    settings: Neo4jSettings
    index_settings: GraphIndexSettings
    embedding_client: EmbeddingClient

    def __post_init__(self) -> None:
        self._driver = GraphDatabase.driver(
            self.settings.uri,
            auth=(self.settings.username, self.settings.password),
        )

    @classmethod
    def from_defaults(
        cls,
        *,
        settings: Neo4jSettings | None = None,
        index_settings: GraphIndexSettings | None = None,
        openai_settings: OpenAISettings | None = None,
        embedding_client: EmbeddingClient | None = None,
    ) -> "AssistantToolkit":
        settings = settings or load_settings()
        index_settings = index_settings or load_index_settings()
        if embedding_client is None:
            openai_settings = openai_settings or load_openai_settings()
            embedding_client = OpenAIEmbeddingClient(
                api_key=openai_settings.api_key,
                model=openai_settings.model,
                api_base=openai_settings.api_base,
                dimension=index_settings.vector_dimensions,
            )
        return cls(
            settings=settings,
            index_settings=index_settings,
            embedding_client=embedding_client,
        )

    # Core tools ------------------------------------------------------------------
    def search_nodes(
        self,
        query: str,
        *,
        top_k: int = 5,
        label: str | None = None,
    ) -> List[Dict[str, Any]]:
        embedding = self.embedding_client.embed_documents([query])[0]
        seen: set[str] = set()
        results: List[Dict[str, Any]] = []

        vector_matches = self._vector_search(embedding, top_k=top_k, label=label)
        for match in vector_matches:
            results.append(match)
            node_id = match.get("node", {}).get("id")
            if node_id:
                seen.add(node_id)

        keyword_matches = self._keyword_search(query, top_k=top_k, label=label, seen=seen)
        results.extend(keyword_matches)

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
        return {
            "node": node_props,
            "summary": node_props.get("summary"),
            "neighbors": self.get_neighbors(node_id, depth=1),
        }

    def close(self) -> None:
        self._driver.close()

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

    def _vector_search(
        self,
        embedding: Sequence[float],
        *,
        top_k: int,
        label: str | None,
    ) -> List[Dict[str, Any]]:
        try:
            with self._driver.session(database=self.settings.database) as session:
                records = session.run(
                    """
                    CALL db.index.vector.queryNodes($indexName, $topK, $embedding)
                    YIELD node, score
                    WITH node, score
                    WHERE $label IS NULL OR node.searchLabel = $label
                    RETURN node, score
                    """,
                    indexName=self.index_settings.vector_index,
                    topK=top_k,
                    embedding=self._vector_to_list(embedding),
                    label=label,
                )
                return [
                    self._format_match(record["node"], record["score"], source="vector")
                    for record in records
                ]
        except Neo4jError:
            return []

    def _keyword_search(
        self,
        query: str,
        *,
        top_k: int,
        label: str | None,
        seen: set[str],
    ) -> List[Dict[str, Any]]:
        try:
            with self._driver.session(database=self.settings.database) as session:
                records = session.run(
                    """
                    CALL db.index.fulltext.queryNodes($indexName, $query)
                    YIELD node, score
                    WITH node, score
                    WHERE $label IS NULL OR node.searchLabel = $label
                    RETURN node, score
                    ORDER BY score DESC
                    LIMIT $topK
                    """,
                    indexName=self.index_settings.keyword_index,
                    query=query,
                    label=label,
                    topK=top_k,
                )
                matches = []
                for record in records:
                    node_props = self._node_to_dict(record["node"])
                    node_id = node_props.get("id")
                    if node_id and node_id in seen:
                        continue
                    matches.append(
                        self._format_match(node_props, record["score"], source="keyword")
                    )
                return matches
        except Neo4jError:
            return []

    def _format_match(self, node, score: float, *, source: str) -> Dict[str, Any]:
        node_props = node if isinstance(node, dict) else self._node_to_dict(node)
        return {
            "matchScore": float(score),
            "source": source,
            "node": node_props,
            "text": node_props.get("summary"),
            "metadata": node_props.get("searchMetadata"),
        }

    def _node_to_dict(self, node) -> Dict[str, Any]:
        props = dict(node)
        props["labels"] = list(node.labels)
        return props

    def _vector_to_list(self, vector: Sequence[float]) -> List[float]:
        if isinstance(vector, np.ndarray):
            return vector.astype(float).tolist()
        return [float(v) for v in vector]


