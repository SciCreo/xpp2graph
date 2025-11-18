"""
Embedding generation pipeline for Codex AOTGraph.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Sequence

import numpy as np
from neo4j import GraphDatabase

from src.config import Neo4jSettings, load_settings
from src.embeddings.client import EmbeddingClient, HashEmbeddingClient
from src.embeddings.store import LocalVectorStore, VectorEntry, VectorMatch
from src.embeddings.text import NodeText, NodeTextBuilder


@dataclass
class EmbeddingPipeline:
    settings: Neo4jSettings
    embedding_client: EmbeddingClient
    store: LocalVectorStore
    labels: Sequence[str] = ("Method", "Class", "Table", "Field")

    @classmethod
    def default(
        cls,
        *,
        store_path: Path,
        embedding_client: EmbeddingClient | None = None,
        settings: Neo4jSettings | None = None,
    ) -> "EmbeddingPipeline":
        settings = settings or load_settings()
        embedding_client = embedding_client or HashEmbeddingClient()
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store = LocalVectorStore(store_path, dimension=embedding_client.dimension)
        return cls(settings=settings, embedding_client=embedding_client, store=store)

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
                entries = [
                    VectorEntry(
                        node_id=node.node_id,
                        label=node.label,
                        vector=embeddings[idx],
                        text=node.text,
                        metadata=node.metadata,
                    )
                    for idx, node in enumerate(batch)
                ]
                self.store.upsert(entries)
                total += len(entries)
        finally:
            driver.close()
        return total

    def similarity_search(
        self,
        query: str,
        *,
        top_k: int = 5,
        label: str | None = None,
    ) -> List[VectorMatch]:
        embedding = self.embedding_client.embed_documents([query])[0]
        return self.store.similarity_search(embedding, top_k=top_k, label=label)

    def close(self) -> None:
        self.store.close()

    @staticmethod
    def _filter_node_texts(
        iterator: Iterator[NodeText],
        allowed_labels: set[str],
    ) -> Iterator[NodeText]:
        for node_text in iterator:
            if node_text.label in allowed_labels:
                yield node_text


def _batched(iterator: Iterator[NodeText], size: int) -> Iterator[List[NodeText]]:
    batch = []
    for item in iterator:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch



