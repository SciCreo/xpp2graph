"""
Utilities that build textual representations of graph nodes for embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List

from neo4j import Driver


@dataclass
class NodeText:
    node_id: str
    label: str
    text: str
    metadata: dict[str, object]


class NodeTextBuilder:
    """Generates text payloads for graph nodes to feed into the embeddings layer."""

    def __init__(self, driver: Driver, database: str = "neo4j") -> None:
        self._driver = driver
        self._database = database

    def iter_node_texts(self) -> Iterator[NodeText]:
        yield from self.iter_methods()
        yield from self.iter_classes()
        yield from self.iter_tables()
        yield from self.iter_fields()

    def iter_methods(self) -> Iterator[NodeText]:
        query = """
        MATCH (m:Method)
        OPTIONAL MATCH (m)-[:CALLS]->(called:Method)
        OPTIONAL MATCH (caller:Method)-[:CALLS]->(m)
        OPTIONAL MATCH (m)-[:READS_FIELD]->(readField:Field)
        OPTIONAL MATCH (m)-[:WRITES_FIELD]->(writeField:Field)
        WITH m,
             collect(DISTINCT called) AS calledMethods,
             collect(DISTINCT caller) AS callerMethods,
             collect(DISTINCT readField) AS readFields,
             collect(DISTINCT writeField) AS writeFields
        RETURN m, calledMethods, callerMethods, readFields, writeFields
        """
        for record in self._run(query):
            method = record["m"]
            called_methods = [_format_method_short(node) for node in record["calledMethods"]]
            caller_methods = [_format_method_short(node) for node in record["callerMethods"]]
            read_fields = [_format_field_short(node) for node in record["readFields"]]
            write_fields = [_format_field_short(node) for node in record["writeFields"]]

            text_lines = [
                f"Method {method['className']}.{method['name']} (model={method['model']}, access={method.get('access')}, static={method.get('isStatic')})",
                f"Declared in class: {method['className']}",
            ]
            if called_methods:
                text_lines.append("Calls: " + ", ".join(called_methods))
            if caller_methods:
                text_lines.append("Called by: " + ", ".join(caller_methods))
            if read_fields:
                text_lines.append("Reads fields: " + ", ".join(read_fields))
            if write_fields:
                text_lines.append("Writes fields: " + ", ".join(write_fields))

            metadata = {
                "label": "Method",
                "className": method["className"],
                "model": method["model"],
            }

            yield NodeText(
                node_id=method["id"],
                label="Method",
                text="\n".join(text_lines),
                metadata=metadata,
            )

    def iter_classes(self) -> Iterator[NodeText]:
        query = """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:DECLARES_METHOD]->(m:Method)
        OPTIONAL MATCH (c)-[:EXTENDS]->(base:Class)
        WITH c,
             collect(DISTINCT m) AS methods,
             collect(DISTINCT base) AS baseClasses
        RETURN c, methods, baseClasses
        """
        for record in self._run(query):
            cls = record["c"]
            methods = [_format_method_short(node) for node in record["methods"]]
            base_classes = [node["name"] for node in record["baseClasses"] if node]

            text_lines = [
                f"Class {cls['name']} (model={cls['model']})",
            ]
            if base_classes:
                text_lines.append("Extends: " + ", ".join(base_classes))
            if methods:
                text_lines.append("Methods: " + ", ".join(methods))

            metadata = {
                "label": "Class",
                "model": cls["model"],
            }

            yield NodeText(
                node_id=cls["id"],
                label="Class",
                text="\n".join(text_lines),
                metadata=metadata,
            )

    def iter_tables(self) -> Iterator[NodeText]:
        query = """
        MATCH (t:Table)
        OPTIONAL MATCH (t)-[:HAS_FIELD]->(f:Field)
        WITH t, collect(DISTINCT f) AS fields
        RETURN t, fields
        """
        for record in self._run(query):
            table = record["t"]
            fields = [_format_field_short(node) for node in record["fields"]]

            text_lines = [
                f"Table {table['name']} (model={table['model']})",
            ]
            if fields:
                text_lines.append("Fields: " + ", ".join(fields))

            metadata = {
                "label": "Table",
                "model": table["model"],
            }

            yield NodeText(
                node_id=table["id"],
                label="Table",
                text="\n".join(text_lines),
                metadata=metadata,
            )

    def iter_fields(self) -> Iterator[NodeText]:
        query = """
        MATCH (f:Field)<-[:HAS_FIELD]-(t:Table)
        OPTIONAL MATCH (m:Method)-[:READS_FIELD]->(f)
        OPTIONAL MATCH (m2:Method)-[:WRITES_FIELD]->(f)
        WITH f, t,
             collect(DISTINCT m) AS readers,
             collect(DISTINCT m2) AS writers
        RETURN f, t, readers, writers
        """
        for record in self._run(query):
            field = record["f"]
            table = record["t"]
            readers = [_format_method_short(node) for node in record["readers"]]
            writers = [_format_method_short(node) for node in record["writers"]]

            text_lines = [
                f"Field {table['name']}.{field['name']} (model={field['model']}, type={field.get('fieldType')}, edt={field.get('extendedDataType')})",
            ]
            if readers:
                text_lines.append("Read by: " + ", ".join(readers))
            if writers:
                text_lines.append("Written by: " + ", ".join(writers))

            metadata = {
                "label": "Field",
                "model": field["model"],
                "tableName": table["name"],
            }

            yield NodeText(
                node_id=field["id"],
                label="Field",
                text="\n".join(text_lines),
                metadata=metadata,
            )

    def _run(self, query: str):
        with self._driver.session(database=self._database) as session:
            result = session.run(query)
            return list(result)


def _format_method_short(node: Dict[str, object]) -> str:
    if not node:
        return ""
    return f"{node.get('className')}.{node.get('name')}"


def _format_field_short(node: Dict[str, object]) -> str:
    if not node:
        return ""
    return f"{node.get('tableName')}.{node.get('name')}"


