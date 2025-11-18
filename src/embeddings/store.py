"""
Simple SQLite-backed vector store for Codex AOTGraph.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np


@dataclass
class VectorEntry:
    node_id: str
    label: str
    vector: np.ndarray
    text: str
    metadata: dict[str, object] | None = None


@dataclass
class VectorMatch:
    node_id: str
    label: str
    score: float
    text: str
    metadata: dict[str, object] | None


class LocalVectorStore:
    """
    Minimal vector store that persists embeddings in an on-disk SQLite database.
    """

    def __init__(self, path: Path, dimension: int) -> None:
        self._path = path
        self._dimension = dimension
        self._connection = sqlite3.connect(self._path)
        self._connection.execute("PRAGMA journal_mode=WAL;")
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                node_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                vector BLOB NOT NULL,
                text TEXT NOT NULL,
                metadata TEXT
            )
            """
        )
        self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_embeddings_label
            ON embeddings(label)
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def upsert(self, entries: Iterable[VectorEntry]) -> None:
        with self._connection:
            self._connection.executemany(
                """
                INSERT INTO embeddings (node_id, label, vector, text, metadata)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    label=excluded.label,
                    vector=excluded.vector,
                    text=excluded.text,
                    metadata=excluded.metadata
                """,
                [
                    (
                        entry.node_id,
                        entry.label,
                        entry.vector.astype(np.float32).tobytes(),
                        entry.text,
                        json.dumps(entry.metadata or {}),
                    )
                    for entry in entries
                ],
            )

    def fetch(self, node_id: str) -> VectorEntry | None:
        cursor = self._connection.execute(
            "SELECT node_id, label, vector, text, metadata FROM embeddings WHERE node_id = ?",
            (node_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        node_id, label, vector_blob, text, metadata_json = row
        vector = np.frombuffer(vector_blob, dtype=np.float32)
        metadata = json.loads(metadata_json) if metadata_json else {}
        return VectorEntry(
            node_id=node_id,
            label=label,
            vector=vector,
            text=text,
            metadata=metadata,
        )

    def similarity_search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 10,
        label: str | None = None,
    ) -> List[VectorMatch]:
        if query_vector.shape[0] != self._dimension:
            raise ValueError("Query vector has unexpected dimension")

        cursor = self._connection.cursor()
        if label:
            cursor.execute(
                "SELECT node_id, label, vector, text, metadata FROM embeddings WHERE label = ?",
                (label,),
            )
        else:
            cursor.execute("SELECT node_id, label, vector, text, metadata FROM embeddings")

        rows = cursor.fetchall()
        if not rows:
            return []

        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            raise ValueError("Query vector norm is zero")

        matches: List[VectorMatch] = []
        for node_id, node_label, vector_blob, text, metadata_json in rows:
            vector = np.frombuffer(vector_blob, dtype=np.float32)
            if vector.shape[0] != self._dimension:
                continue
            score = float(np.dot(query_vector, vector) / (query_norm * np.linalg.norm(vector)))
            metadata = json.loads(metadata_json) if metadata_json else {}
            matches.append(
                VectorMatch(
                    node_id=node_id,
                    label=node_label,
                    score=score,
                    text=text,
                    metadata=metadata,
                )
            )

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:top_k]


