"""
Centralized application settings.

Environment variables drive configuration so that deployments can override
defaults without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Neo4jSettings:
    """Connection parameters for Neo4j."""

    uri: str
    username: str
    password: str
    database: str = "neo4j"


def load_settings() -> Neo4jSettings:
    """
    Load Neo4j configuration from environment variables.

    Required vars:
        CODXA_NEO4J_URI
        CODXA_NEO4J_USER
        CODXA_NEO4J_PASSWORD

    Optional:
        CODXA_NEO4J_DATABASE (defaults to \"neo4j\")
    """

    uri = os.environ.get("CODXA_NEO4J_URI")
    username = os.environ.get("CODXA_NEO4J_USER")
    password = os.environ.get("CODXA_NEO4J_PASSWORD")
    database = os.environ.get("CODXA_NEO4J_DATABASE", "neo4j")

    if not uri or not username or not password:
        raise RuntimeError("Neo4j configuration missing required environment variables")

    return Neo4jSettings(uri=uri, username=username, password=password, database=database)


@dataclass(frozen=True)
class OpenAISettings:
    """Configuration for OpenAI embeddings."""

    api_key: str
    model: str = "text-embedding-3-large"
    api_base: Optional[str] = None


def load_openai_settings(required: bool = True) -> Optional[OpenAISettings]:
    """
    Load OpenAI configuration. If required is False and the API key is missing,
    return None instead of raising.
    """

    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-large")
    api_base = os.environ.get("OPENAI_API_BASE")

    if not api_key:
        if required:
            raise RuntimeError("OPENAI_API_KEY environment variable is required")
        return None

    return OpenAISettings(api_key=api_key, model=model, api_base=api_base)


@dataclass(frozen=True)
class GraphIndexSettings:
    """Names for Neo4j keyword and vector indexes used by Codex AOTGraph."""

    keyword_index: str = "codex_keyword_index"
    vector_index: str = "codex_vector_index"
    vector_dimensions: int = 2048


def load_index_settings() -> GraphIndexSettings:
    keyword_index = os.environ.get("CODXA_KEYWORD_INDEX_NAME", "codex_keyword_index")
    vector_index = os.environ.get("CODXA_VECTOR_INDEX_NAME", "codex_vector_index")
    vector_dimensions = int(os.environ.get("CODXA_VECTOR_DIMENSIONS", "2048"))
    return GraphIndexSettings(
        keyword_index=keyword_index,
        vector_index=vector_index,
        vector_dimensions=vector_dimensions,
    )


