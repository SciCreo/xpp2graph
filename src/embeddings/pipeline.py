"""
Embedding generation pipeline for Codex AOTGraph.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, List, Sequence

import numpy as np
from neo4j import GraphDatabase

from src.config import (
    GraphIndexSettings,
    Neo4jSettings,
    OpenAISettings,
    load_index_settings,
    load_openai_settings,
    load_settings,
)
from src.embeddings.client import EmbeddingClient, OpenAIEmbeddingClient
from src.embeddings.text import NodeText, NodeTextBuilder


@dataclass
class EmbeddingPipeline:
    settings: Neo4jSettings
    embedding_client: EmbeddingClient
    index_settings: GraphIndexSettings
    labels: Sequence[str] = ("Method", "Class", "Table", "Field")

    @classmethod
    def default(
        cls,
        *,
        settings: Neo4jSettings | None = None,
        openai_settings: OpenAISettings | None = None,
        embedding_client: EmbeddingClient | None = None,
        index_settings: GraphIndexSettings | None = None,
    ) -> "EmbeddingPipeline":
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
            embedding_client=embedding_client,
            index_settings=index_settings,
        )

    def run(self, labels: Sequence[str] | None = None, batch_size: int = 64) -> int:
        labels = labels or self.labels
        driver = GraphDatabase.driver(
            self.settings.uri,
            auth=(self.settings.username, self.settings.password),
        )
        builder = NodeTextBuilder(driver, database=self.settings.database)
        total = 0
        try:
            node_texts = self._filter_node_texts(builder.iter_node_texts(), set(labels))
            for batch in _batched(node_texts, batch_size):
                texts = [node.text for node in batch]
                embeddings = self.embedding_client.embed_documents(texts)
                rows = [
                    {
                        "id": node.node_id,
                        "summary": node.text,
                        "embedding": self._vector_to_list(embeddings[idx]),
                        "metadata": node.metadata,
                        "label": node.label,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    for idx, node in enumerate(batch)
                ]
                if rows:
                    self._upsert_embeddings(driver, rows)
                    total += len(rows)
        finally:
            driver.close()
        return total

    @staticmethod
    def _filter_node_texts(
        iterator: Iterator[NodeText],
        allowed_labels: set[str],
    ) -> Iterator[NodeText]:
        for node_text in iterator:
            if node_text.label in allowed_labels:
                yield node_text

    def _vector_to_list(self, vector: np.ndarray | Sequence[float]) -> List[float]:
        if isinstance(vector, np.ndarray):
            values = vector.astype(float).tolist()
        else:
            values = [float(v) for v in vector]

        target_dim = self.index_settings.vector_dimensions
        if target_dim:
            if len(values) > target_dim:
                values = values[:target_dim]
            elif len(values) < target_dim:
                values = values + [0.0] * (target_dim - len(values))
        return values

    def _upsert_embeddings(self, driver, rows: List[dict]) -> None:
        with driver.session(database=self.settings.database) as session:
            session.run(
                """
                UNWIND $rows AS row
                MATCH (n {id: row.id})
                SET n.summary = row.summary,
                    n.embedding = row.embedding,
                    n.embeddingModel = $model,
                    n.searchLabel = row.label,
                    n.searchMetadata = row.metadata,
                    n.searchUpdatedAt = row.updated_at,
                    n:Searchable
                """,
                rows=rows,
                model=self.embedding_client.model_name,
            )


def _batched(iterator: Iterator[NodeText], size: int) -> Iterator[List[NodeText]]:
    batch = []
    for item in iterator:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch



