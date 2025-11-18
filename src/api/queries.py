"""
High-level graph queries exposed via the Codex AOTGraph API.
"""

from __future__ import annotations

from typing import Any, Dict, List

from neo4j import Driver

from src.api.models import ClassHierarchy, ClassRef, FieldRef, MethodRef, WhereUsedResponse, FieldAccessResponse


class GraphQueryService:
    """Executes Cypher queries backing the REST API endpoints."""

    def __init__(self, driver: Driver, database: str = "neo4j") -> None:
        self._driver = driver
        self._database = database

    # Public API ------------------------------------------------------------------
    def where_used_method(
        self,
        *,
        class_name: str,
        method_name: str,
        model: str | None = None,
    ) -> WhereUsedResponse:
        target = self._fetch_single_method(class_name, method_name, model)
        callers = self._fetch_callers(target["id"])
        return WhereUsedResponse(
            target=_to_method_ref(target),
            callers=[_to_method_ref(caller) for caller in callers],
        )

    def field_access(
        self,
        *,
        table_name: str,
        field_name: str,
        model: str | None = None,
    ) -> FieldAccessResponse:
        field = self._fetch_field(table_name, field_name, model)
        readers = self._fetch_field_methods(field["id"], rel_type="READS_FIELD")
        writers = self._fetch_field_methods(field["id"], rel_type="WRITES_FIELD")
        return FieldAccessResponse(
            field=_to_field_ref(field),
            readers=[_to_method_ref(method) for method in readers],
            writers=[_to_method_ref(method) for method in writers],
        )

    def class_hierarchy(
        self,
        *,
        class_name: str,
        model: str | None = None,
    ) -> ClassHierarchy:
        class_node = self._fetch_class(class_name, model)
        base_classes = [
            _to_class_ref(node) for node in self._fetch_class_hierarchy(class_node["id"])
        ]
        return ClassHierarchy(
            id=class_node["id"],
            name=class_node["name"],
            model=class_node["model"],
            baseClasses=base_classes,
        )

    # Query helpers ----------------------------------------------------------------
    def _fetch_single_method(
        self,
        class_name: str,
        method_name: str,
        model: str | None,
    ) -> Dict[str, Any]:
        query = """
        MATCH (m:Method)
        WHERE m.className = $className
          AND m.name = $methodName
          AND ($model IS NULL OR m.model = $model)
        RETURN m LIMIT 1
        """
        record = self._run_single(query, className=class_name, methodName=method_name, model=model)
        if not record:
            raise LookupError(f"Method {class_name}.{method_name} not found")
        return record["m"]

    def _fetch_callers(self, method_id: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (caller:Method)-[:CALLS]->(target:Method {id: $methodId})
        RETURN caller ORDER BY caller.className, caller.name
        """
        return [record["caller"] for record in self._run(query, methodId=method_id)]

    def _fetch_field(
        self,
        table_name: str,
        field_name: str,
        model: str | None,
    ) -> Dict[str, Any]:
        query = """
        MATCH (f:Field)
        WHERE f.tableName = $tableName
          AND f.name = $fieldName
          AND ($model IS NULL OR f.model = $model)
        RETURN f LIMIT 1
        """
        record = self._run_single(query, tableName=table_name, fieldName=field_name, model=model)
        if not record:
            raise LookupError(f"Field {table_name}.{field_name} not found")
        return record["f"]

    def _fetch_field_methods(self, field_id: str, *, rel_type: str) -> List[Dict[str, Any]]:
        query = f"""
        MATCH (m:Method)-[:{rel_type}]->(f:Field {{id: $fieldId}})
        RETURN m ORDER BY m.className, m.name
        """
        return [record["m"] for record in self._run(query, fieldId=field_id)]

    def _fetch_class(self, class_name: str, model: str | None) -> Dict[str, Any]:
        query = """
        MATCH (c:Class)
        WHERE c.name = $className
          AND ($model IS NULL OR c.model = $model)
        RETURN c LIMIT 1
        """
        record = self._run_single(query, className=class_name, model=model)
        if not record:
            raise LookupError(f"Class {class_name} not found")
        return record["c"]

    def _fetch_class_hierarchy(self, class_id: str) -> List[str]:
        query = """
        MATCH path = (c:Class {id: $classId})-[:EXTENDS*]->(base:Class)
        RETURN base AS node
        ORDER BY length(path)
        """
        return [record["node"] for record in self._run(query, classId=class_id)]

    # Execution helpers -----------------------------------------------------------
    def _run(self, query: str, **parameters: Any):
        with self._driver.session(database=self._database) as session:
            result = session.run(query, **parameters)
            return list(result)

    def _run_single(self, query: str, **parameters: Any):
        with self._driver.session(database=self._database) as session:
            result = session.run(query, **parameters)
            return result.single()


def _to_method_ref(node: Dict[str, Any]) -> MethodRef:
    return MethodRef(
        id=node["id"],
        name=node["name"],
        className=node["className"],
        model=node["model"],
    )


def _to_field_ref(node: Dict[str, Any]) -> FieldRef:
    return FieldRef(
        id=node["id"],
        name=node["name"],
        tableName=node["tableName"],
        model=node["model"],
    )


def _to_class_ref(node: Dict[str, Any]) -> ClassRef:
    return ClassRef(
        id=node["id"],
        name=node["name"],
        model=node["model"],
    )


