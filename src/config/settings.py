"""
Centralized application settings.

Environment variables drive configuration so that deployments can override
defaults without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


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


