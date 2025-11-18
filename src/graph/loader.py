"""
Neo4j loader utilities for Codex AOTGraph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from neo4j import Driver, GraphDatabase, Session

from src.config import GraphIndexSettings, Neo4jSettings
from src.graph.schema import (
    DEFAULT_SCHEMA,
    SchemaMetadata,
    format_node_properties,
    NODE_CLASS,
    NODE_FIELD,
    NODE_METHOD,
    NODE_MODEL,
    NODE_PACKAGE,
    NODE_TABLE,
    REL_BELONGS_TO_MODEL,
    REL_BELONGS_TO_PACKAGE,
    REL_CALLS,
    REL_DECLARES_METHOD,
    REL_EXTENDS,
    REL_HAS_FIELD,
    REL_READS_FIELD,
    REL_WRITES_FIELD,
)
from src.ir import ClassIR, FieldIR, MethodIR, TableIR
from src.ir.models import FieldAccessType


@dataclass
SEARCHABLE_LABEL = "Searchable"


@dataclass
class GraphLoader:
    """High-level helper that persists IR objects into Neo4j."""

    settings: Neo4jSettings
    schema: SchemaMetadata = DEFAULT_SCHEMA
    index_settings: GraphIndexSettings = GraphIndexSettings()
    driver: Driver | None = None

    def __post_init__(self) -> None:
        if self.driver is None:
            auth = (self.settings.username, self.settings.password)
            self.driver = GraphDatabase.driver(self.settings.uri, auth=auth)

    def close(self) -> None:
        if self.driver:
            self.driver.close()

    def _session(self) -> Session:
        if not self.driver:
            raise RuntimeError("Neo4j driver is not initialized")
        return self.driver.session(database=self.settings.database)

    # Constraint/index management -------------------------------------------------
    def ensure_constraints(self) -> None:
        with self._session() as session:
            for label, key in self.schema.node_keys.items():
                constraint_query = (
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) "
                    f"REQUIRE n.{key} IS UNIQUE"
                )
                session.run(constraint_query)

            for label, indexes in self.schema.node_indexes.items():
                for index_property in indexes:
                    index_query = (
                        f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) "
                        f"ON (n.{index_property})"
                    )
                    session.run(index_query)

    def ensure_indexes(self) -> None:
        with self._session() as session:
            keyword_query = (
                f"CREATE FULLTEXT INDEX {self.index_settings.keyword_index} IF NOT EXISTS "
                f"FOR (n:{SEARCHABLE_LABEL}) ON EACH [n.summary, n.name, n.aotPath]"
            )
            session.run(keyword_query)

            vector_query = (
                f"CREATE VECTOR INDEX {self.index_settings.vector_index} IF NOT EXISTS "
                f"FOR (n:{SEARCHABLE_LABEL}) ON (n.embedding) "
                "OPTIONS {indexConfig: {`vector.dimensions`: $dimensions, "
                "`vector.similarity_function`: 'cosine'}}"
            )
            session.run(vector_query, dimensions=self.index_settings.vector_dimensions)

    def ensure_schema(self) -> None:
        self.ensure_constraints()
        self.ensure_indexes()

    # Public API -------------------------------------------------------------------
    def sync_ir(self, classes: Sequence[ClassIR], tables: Sequence[TableIR]) -> None:
        """Upsert nodes and relationships for the provided IR objects."""

        self.ensure_schema()

        with self._session() as session:
            for class_ir in classes:
                self._upsert_class(session, class_ir)

            for table_ir in tables:
                self._upsert_table(session, table_ir)

            for class_ir in classes:
                self._upsert_method_relationships(session, class_ir)

    # Internal helpers -------------------------------------------------------------
    def _upsert_class(self, session: Session, class_ir: ClassIR) -> None:
        properties = format_node_properties(
            {
                "id": class_ir.element_id(),
                "name": class_ir.name,
                "aotPath": class_ir.aot_path,
                "model": class_ir.model,
                "package": class_ir.package,
                "layer": class_ir.layer,
                "baseClass": class_ir.base_class,
            }
        )
        self._merge_node(session, NODE_CLASS, properties)

        self._merge_model_relations(
            session=session,
            node_label=NODE_CLASS,
            node_id=class_ir.element_id(),
            model_name=class_ir.model,
            package_name=class_ir.package,
        )

        for method_ir in class_ir.methods.values():
            self._upsert_method(session, method_ir)
            self._merge_relationship(
                session,
                start_label=NODE_CLASS,
                start_id=class_ir.element_id(),
                rel_type=REL_DECLARES_METHOD,
                end_label=NODE_METHOD,
                end_id=method_ir.element_id(),
            )

        if class_ir.base_class:
            base_id = parse_related_class_id(class_ir.base_class, class_ir.model)
            if base_id:
                self._merge_relationship(
                    session,
                    start_label=NODE_CLASS,
                    start_id=class_ir.element_id(),
                    rel_type=REL_EXTENDS,
                    end_label=NODE_CLASS,
                    end_id=base_id,
                )

    def _upsert_method(self, session: Session, method_ir: MethodIR) -> None:
        properties = format_node_properties(
            {
                "id": method_ir.element_id(),
                "name": method_ir.name,
                "aotPath": method_ir.aot_path,
                "model": method_ir.model,
                "className": method_ir.class_name,
                "access": method_ir.access.value,
                "isStatic": method_ir.is_static,
                "lineCount": method_ir.line_count,
                "body": method_ir.body,
            }
        )
        self._merge_node(session, NODE_METHOD, properties)

    def _upsert_table(self, session: Session, table_ir: TableIR) -> None:
        properties = format_node_properties(
            {
                "id": table_ir.element_id(),
                "name": table_ir.name,
                "aotPath": table_ir.aot_path,
                "model": table_ir.model,
                "package": table_ir.package,
                "layer": table_ir.layer,
            }
        )
        self._merge_node(session, NODE_TABLE, properties)

        self._merge_model_relations(
            session=session,
            node_label=NODE_TABLE,
            node_id=table_ir.element_id(),
            model_name=table_ir.model,
            package_name=table_ir.package,
        )

        for field_ir in table_ir.fields.values():
            self._upsert_field(session, field_ir)
            self._merge_relationship(
                session,
                start_label=NODE_TABLE,
                start_id=table_ir.element_id(),
                rel_type=REL_HAS_FIELD,
                end_label=NODE_FIELD,
                end_id=field_ir.element_id(),
            )

    def _upsert_field(self, session: Session, field_ir: FieldIR) -> None:
        properties = format_node_properties(
            {
                "id": field_ir.element_id(),
                "name": field_ir.name,
                "aotPath": field_ir.aot_path,
                "model": field_ir.model,
                "tableName": field_ir.table_name,
                "extendedDataType": field_ir.extended_data_type,
                "fieldType": field_ir.field_type,
            }
        )
        self._merge_node(session, NODE_FIELD, properties)

    def _upsert_method_relationships(self, session: Session, class_ir: ClassIR) -> None:
        for method_ir in class_ir.methods.values():
            for target_method_id in method_ir.called_methods:
                self._merge_relationship(
                    session,
                    start_label=NODE_METHOD,
                    start_id=method_ir.element_id(),
                    rel_type=REL_CALLS,
                    end_label=NODE_METHOD,
                    end_id=target_method_id,
                )

            for access in method_ir.field_accesses:
                rel_type = REL_READS_FIELD if access.access_type == FieldAccessType.READ else REL_WRITES_FIELD
                self._merge_relationship(
                    session,
                    start_label=NODE_METHOD,
                    start_id=method_ir.element_id(),
                    rel_type=rel_type,
                    end_label=NODE_FIELD,
                    end_id=access.target_field_id(),
                )

    # Neo4j helpers ----------------------------------------------------------------
    def _merge_node(self, session: Session, label: str, properties: dict) -> None:
        node_id = properties.get("id")
        if not node_id:
            raise ValueError(f"Node properties for label {label} missing 'id'")

        session.run(
            f"MERGE (n:{label} {{id: $id}}) "
            f"SET n += $props",
            id=node_id,
            props=properties,
        )

    def _merge_relationship(
        self,
        session: Session,
        *,
        start_label: str,
        start_id: str,
        rel_type: str,
        end_label: str,
        end_id: str,
    ) -> None:
        session.run(
            f"MATCH (start:{start_label} {{id: $start_id}}) "
            f"MATCH (end:{end_label} {{id: $end_id}}) "
            f"MERGE (start)-[r:{rel_type}]->(end)",
            start_id=start_id,
            end_id=end_id,
        )

    def _merge_model_relations(
        self,
        *,
        session: Session,
        node_label: str,
        node_id: str,
        model_name: str,
        package_name: str | None,
    ) -> None:
        model_properties = {"id": model_name, "name": model_name}
        self._merge_node(session, NODE_MODEL, model_properties)
        self._merge_relationship(
            session,
            start_label=node_label,
            start_id=node_id,
            rel_type=REL_BELONGS_TO_MODEL,
            end_label=NODE_MODEL,
            end_id=model_name,
        )

        if package_name:
            package_properties = {"id": package_name, "name": package_name}
            self._merge_node(session, NODE_PACKAGE, package_properties)
            self._merge_relationship(
                session,
                start_label=node_label,
                start_id=node_id,
                rel_type=REL_BELONGS_TO_PACKAGE,
                end_label=NODE_PACKAGE,
                end_id=package_name,
            )


def parse_related_class_id(class_reference: str, fallback_model: str) -> str | None:
    """
    Convert a reference such as \"Model/ClassName\" or \"ClassName\" into a class ID.
    """

    if "/" in class_reference:
        return class_reference
    if class_reference:
        return f"{fallback_model}/{class_reference}"
    return None


