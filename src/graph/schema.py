"""
Centralized definitions for the Neo4j schema used by Codex AOTGraph.

The loader module relies on the metadata in this file to create indexes,
constraints, and to keep relationship semantics consistent across imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence


NODE_CLASS = "Class"
NODE_METHOD = "Method"
NODE_TABLE = "Table"
NODE_FIELD = "Field"
NODE_MODEL = "Model"
NODE_PACKAGE = "Package"

REL_EXTENDS = "EXTENDS"
REL_DECLARES_METHOD = "DECLARES_METHOD"
REL_HAS_FIELD = "HAS_FIELD"
REL_CALLS = "CALLS"
REL_READS_FIELD = "READS_FIELD"
REL_WRITES_FIELD = "WRITES_FIELD"
REL_BELONGS_TO_MODEL = "BELONGS_TO_MODEL"
REL_BELONGS_TO_PACKAGE = "BELONGS_TO_PACKAGE"


@dataclass(frozen=True)
class SchemaMetadata:
    """
    Encapsulates node and relationship configurations required by the loader.

    Attributes:
        node_keys: Mapping of node label -> property used as unique identifier.
        node_indexes: Mapping of node label -> sequence of additional indexed properties.
        relationship_types: Sequence of supported relationship type names.
    """

    node_keys: Mapping[str, str]
    node_indexes: Mapping[str, Sequence[str]]
    relationship_types: Sequence[str]


DEFAULT_SCHEMA = SchemaMetadata(
    node_keys={
        NODE_CLASS: "id",
        NODE_METHOD: "id",
        NODE_TABLE: "id",
        NODE_FIELD: "id",
        NODE_MODEL: "id",
        NODE_PACKAGE: "id",
    },
    node_indexes={
        NODE_CLASS: ("name", "model"),
        NODE_METHOD: ("name", "className", "model"),
        NODE_TABLE: ("name", "model"),
        NODE_FIELD: ("name", "tableName", "model"),
        NODE_MODEL: ("name",),
        NODE_PACKAGE: ("name",),
    },
    relationship_types=(
        REL_EXTENDS,
        REL_DECLARES_METHOD,
        REL_HAS_FIELD,
        REL_CALLS,
        REL_READS_FIELD,
        REL_WRITES_FIELD,
        REL_BELONGS_TO_MODEL,
        REL_BELONGS_TO_PACKAGE,
    ),
)


def format_node_properties(payload: Dict[str, object]) -> Dict[str, object]:
    """
    Normalize node property payloads before upsert.

    Ensures consistent key casing and removes None values so that merges are
    deterministic.
    """

    normalized: Dict[str, object] = {}
    for key, value in payload.items():
        if value is None:
            continue
        normalized[key] = value
    return normalized


