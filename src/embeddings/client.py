"""
Embedding client abstractions for Codex AOTGraph.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import List, Sequence

import numpy as np
from openai import OpenAI


class EmbeddingClient(ABC):
    """Interface for services that convert text into dense vectors."""

    dimension: int
    model_name: str

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
        self.model_name = "hash-embedding"

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


class OpenAIEmbeddingClient(EmbeddingClient):
    """Embedding client backed by OpenAI's embeddings API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        api_base: str | None = None,
        dimension: int | None = None,
    ) -> None:
        client_kwargs = {"api_key": api_key}
        if api_base:
            client_kwargs["base_url"] = api_base
        self._client = OpenAI(**client_kwargs)
        self.model_name = model
        self.dimension = dimension or 0

    def embed_documents(self, texts: Sequence[str]) -> List[np.ndarray]:
        if not texts:
            return []

        response = self._client.embeddings.create(model=self.model_name, input=list(texts))
        embeddings: List[np.ndarray] = []
        for item in response.data:
            vector = np.asarray(item.embedding, dtype=np.float32)
            embeddings.append(vector)

        if not self.dimension and embeddings:
            self.dimension = embeddings[0].shape[0]

        return embeddings


