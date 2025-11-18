"""
Embedding client abstractions for Codex AOTGraph.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import List, Sequence

import numpy as np


class EmbeddingClient(ABC):
    """Interface for services that convert text into dense vectors."""

    dimension: int

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> List[np.ndarray]:
        """Return embeddings for the provided texts."""


class HashEmbeddingClient(EmbeddingClient):
    """
    Deterministic embedding client based on hashing.

    This serves as a placeholder until an external embedding provider (OpenAI,
    Azure, etc.) is wired in. It produces consistent vectors for identical
    strings, which is sufficient for smoke tests and local demos.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: Sequence[str]) -> List[np.ndarray]:
        vectors: List[np.ndarray] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = self._expand_digest(digest, self.dimension)
            vector = np.array(values, dtype=np.float32)
            # Normalize for cosine similarity
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            vectors.append(vector)
        return vectors

    def _expand_digest(self, digest: bytes, dimension: int) -> List[float]:
        values: List[float] = []
        index = 0
        while len(values) < dimension:
            chunk = digest[index % len(digest)]
            normalized = (chunk / 255.0) * 2 - 1
            values.append(normalized)
            index += 1
        return values[:dimension]


