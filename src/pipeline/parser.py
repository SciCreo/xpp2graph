"""
AOT XML parsing utilities for Codex AOTGraph.

The parser favors resilience: it tolerates missing attributes and best-effort
maps nodes into the IR dataclasses defined in `src.ir.models`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple
from xml.etree import ElementTree as ET

from src.ir import ClassIR, FieldIR, FieldAccessIR, FieldAccessType, MethodIR, TableIR
from src.ir.models import AccessModifier, parse_element_id

_CALL_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)::([A-Za-z_][A-Za-z0-9_]*)\b")
_FIELD_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


class AOTParser:
    """Parses AOT XML exports into IR objects."""

    def parse(self, paths: Sequence[Path]) -> Tuple[Dict[str, ClassIR], Dict[str, TableIR]]:
        classes: Dict[str, ClassIR] = {}
        tables: Dict[str, TableIR] = {}

        for path in paths:
            tree = ET.parse(path)
            root = tree.getroot()
            self._walk(root, classes=classes, tables=tables)

        self._populate_field_accesses(classes, tables)
        return classes, tables

    # Walking functions ----------------------------------------------------------
    def _walk(
        self,
        element: ET.Element,
        *,
        classes: Dict[str, ClassIR],
        tables: Dict[str, TableIR],
        current_model: str | None = None,
        current_package: str | None = None,
    ) -> None:
        tag = _strip_namespace(element.tag)

        if tag.lower() in {"model", "package"}:
            current_model = element.attrib.get("Name") or element.attrib.get("name") or current_model
            current_package = element.attrib.get("Name") or element.attrib.get("name") or current_package

        if tag.lower() in {"axclass", "class"}:
            class_ir = self._parse_class(element, current_model, current_package)
            classes[class_ir.element_id()] = class_ir
            return

        if tag.lower() in {"axtable", "table"}:
            table_ir = self._parse_table(element, current_model, current_package)
            tables[table_ir.element_id()] = table_ir
            return

        for child in element:
            self._walk(
                child,
                classes=classes,
                tables=tables,
                current_model=current_model,
                current_package=current_package,
            )

    # Parsers --------------------------------------------------------------------
    def _parse_class(
        self,
        element: ET.Element,
        model: str | None,
        package: str | None,
    ) -> ClassIR:
        name = element.attrib.get("Name") or element.attrib.get("name") or self._find_text(element, "Name")
        if not name:
            raise ValueError("Class element missing name attribute")

        aot_path = element.attrib.get("Id") or element.attrib.get("Path") or name
        layer = element.attrib.get("Layer")
        base_class = self._find_text(element, "Extends") or element.attrib.get("Extends")
        implements = tuple(
            child.text.strip()
            for child in element.findall(".//Implements")
            if child.text and child.text.strip()
        )

        class_ir = ClassIR(
            name=name,
            aot_path=aot_path,
            model=model or "UNKNOWN",
            package=package,
            layer=layer,
            base_class=base_class,
            implements=implements,
        )

        methods_container = self._find_child(element, "Methods")
        if methods_container is None:
            methods_container = element

        for method_element in methods_container:
            tag = _strip_namespace(method_element.tag)
            if tag.lower() not in {"method", "axmethod"}:
                continue
            method_ir = self._parse_method(method_element, class_ir)
            class_ir.add_method(method_ir)

        return class_ir

    def _parse_method(self, element: ET.Element, class_ir: ClassIR) -> MethodIR:
        name = (
            element.attrib.get("Name")
            or element.attrib.get("name")
            or self._find_text(element, "Name")
        )
        if not name:
            raise ValueError(f"Method element in class {class_ir.name} missing name")

        aot_path = element.attrib.get("Id") or element.attrib.get("Path") or f"{class_ir.aot_path}/{name}"
        access = _parse_access_modifier(element)
        is_static = _parse_is_static(element)
        source = self._find_text(element, "Source") or self._find_text(element, "Code")
        line_count = _estimate_line_count(source)

        method_ir = MethodIR(
            name=name,
            aot_path=aot_path,
            model=class_ir.model,
            class_name=class_ir.name,
            access=access,
            is_static=is_static,
            line_count=line_count,
            body=source,
        )

        method_ir.called_methods = self._extract_called_methods(source, class_ir.model)
        return method_ir

    def _parse_table(
        self,
        element: ET.Element,
        model: str | None,
        package: str | None,
    ) -> TableIR:
        name = element.attrib.get("Name") or element.attrib.get("name") or self._find_text(element, "Name")
        if not name:
            raise ValueError("Table element missing name attribute")

        aot_path = element.attrib.get("Id") or element.attrib.get("Path") or name
        layer = element.attrib.get("Layer")

        table_ir = TableIR(
            name=name,
            aot_path=aot_path,
            model=model or "UNKNOWN",
            package=package,
            layer=layer,
        )

        fields_container = self._find_child(element, "Fields")
        if fields_container is None:
            fields_container = element.findall(".//Field") or []
        else:
            fields_container = list(fields_container)

        for field_element in fields_container:
            tag = _strip_namespace(field_element.tag)
            if tag.lower() not in {"field", "axfield"}:
                continue
            field_ir = self._parse_field(field_element, table_ir)
            table_ir.add_field(field_ir)

        return table_ir

    def _parse_field(self, element: ET.Element, table_ir: TableIR) -> FieldIR:
        name = element.attrib.get("Name") or element.attrib.get("name") or self._find_text(element, "Name")
        if not name:
            raise ValueError(f"Field element in table {table_ir.name} missing name")

        aot_path = (
            element.attrib.get("Id")
            or element.attrib.get("Path")
            or f"{table_ir.aot_path}/{name}"
        )
        edt = (
            element.attrib.get("ExtendedDataType")
            or self._find_text(element, "ExtendedDataType")
        )
        field_type = element.attrib.get("Type") or self._find_text(element, "Type")

        return FieldIR(
            name=name,
            aot_path=aot_path,
            table_name=table_ir.name,
            model=table_ir.model,
            extended_data_type=edt,
            field_type=field_type,
        )

    # Field & call extraction -----------------------------------------------------
    def _extract_called_methods(self, source: str | None, model: str) -> list[str]:
        if not source:
            return []

        seen = set()
        results = []
        for class_name, method_name in _CALL_PATTERN.findall(source):
            method_id = parse_element_id(model, class_name, method_name)
            if method_id not in seen:
                seen.add(method_id)
                results.append(method_id)
        return results

    def _populate_field_accesses(
        self,
        classes: Dict[str, ClassIR],
        tables: Dict[str, TableIR],
    ) -> None:
        table_field_lookup = {
            table_ir.name: {field_ir.name for field_ir in table_ir.fields.values()}
            for table_ir in tables.values()
        }

        for class_ir in classes.values():
            for method_ir in class_ir.methods.values():
                method_ir.field_accesses = self._extract_field_accesses(
                    method_ir.body,
                    method_ir.model,
                    table_field_lookup,
                )

    def _extract_field_accesses(
        self,
        source: str | None,
        model: str,
        table_field_lookup: Dict[str, set[str]],
    ) -> list[FieldAccessIR]:
        if not source:
            return []

        accesses: list[FieldAccessIR] = []
        for table_name, field_name in _FIELD_PATTERN.findall(source):
            if table_name not in table_field_lookup:
                continue
            if field_name not in table_field_lookup[table_name]:
                continue
            access_type = FieldAccessType.WRITE if self._is_write(source, table_name, field_name) else FieldAccessType.READ
            accesses.append(
                FieldAccessIR(
                    table_name=table_name,
                    field_name=field_name,
                    model=model,
                    access_type=access_type,
                )
            )
        return accesses

    def _is_write(self, source: str, table_name: str, field_name: str) -> bool:
        assignment_pattern = re.compile(
            rf"{re.escape(table_name)}\.{re.escape(field_name)}\s*:=", re.IGNORECASE
        )
        return bool(assignment_pattern.search(source))

    # Utility helpers -------------------------------------------------------------
    def _find_text(self, element: ET.Element, tag_name: str) -> str | None:
        child = self._find_child(element, tag_name)
        if child is not None and child.text:
            return child.text.strip()
        return None

    def _find_child(self, element: ET.Element, tag_name: str) -> ET.Element | None:
        for child in element:
            if _strip_namespace(child.tag).lower() == tag_name.lower():
                return child
        return None


def _parse_access_modifier(element: ET.Element) -> AccessModifier:
    access_text = element.attrib.get("Access") or element.attrib.get("Modifier")
    if not access_text:
        access_text = _text_from_child(element, "Access")

    access_text = (access_text or "public").lower()
    try:
        return AccessModifier(access_text)
    except ValueError:
        return AccessModifier.PUBLIC


def _parse_is_static(element: ET.Element) -> bool:
    value = element.attrib.get("Static") or element.attrib.get("IsStatic")
    if value is None:
        value = _text_from_child(element, "Static")
    if value is None:
        return False
    return value.strip().lower() in {"true", "yes", "1"}


def _estimate_line_count(source: str | None) -> int | None:
    if not source:
        return None
    return len([line for line in source.splitlines() if line.strip()])


def _text_from_child(element: ET.Element, tag_name: str) -> str | None:
    child = element.find(f".//{tag_name}")
    if child is not None and child.text:
        return child.text.strip()
    return None


