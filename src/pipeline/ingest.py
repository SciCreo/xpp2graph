"""
High-level ingestion pipeline for Codex AOTGraph.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from src.config import Neo4jSettings, load_settings
from src.graph.loader import GraphLoader
from src.graph.schema import SchemaMetadata, DEFAULT_SCHEMA
from src.pipeline.parser import AOTParser


@dataclass(frozen=True)
class IngestionResult:
    classes_processed: int
    methods_processed: int
    tables_processed: int
    fields_processed: int


class IngestionPipeline:
    """
    Coordinates parsing AOT XML exports and synchronising them into Neo4j.
    """

    def __init__(
        self,
        *,
        neo4j_settings: Neo4jSettings | None = None,
        schema: SchemaMetadata = DEFAULT_SCHEMA,
        parser: AOTParser | None = None,
    ) -> None:
        self._settings = neo4j_settings or load_settings()
        self._parser = parser or AOTParser()
        self._schema = schema

    def ingest(self, paths: Sequence[Path]) -> IngestionResult:
        classes, tables = self._parser.parse(paths)
        methods_count = sum(len(class_ir.methods) for class_ir in classes.values())
        fields_count = sum(len(table_ir.fields) for table_ir in tables.values())

        loader = GraphLoader(settings=self._settings, schema=self._schema)
        try:
            loader.sync_ir(list(classes.values()), list(tables.values()))
        finally:
            loader.close()

        return IngestionResult(
            classes_processed=len(classes),
            methods_processed=methods_count,
            tables_processed=len(tables),
            fields_processed=fields_count,
        )


