"""
AOT XML parsing utilities for Codex AOTGraph.

The parser favors resilience: it tolerates missing attributes and best-effort
maps nodes into the IR dataclasses defined in `src.ir.models`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET

from src.ir import ClassIR, FieldIR, FieldAccessIR, FieldAccessType, MethodIR, TableIR
from src.ir.models import AccessModifier, parse_element_id

_CALL_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)::([A-Za-z_][A-Za-z0-9_]*)\b")
_FIELD_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


class AOTParser:
    """Parses AOT XML exports into IR objects."""

    def __init__(self) -> None:
        self._current_file: Optional[Path] = None

    def parse(self, paths: Sequence[Path]) -> Tuple[Dict[str, ClassIR], Dict[str, TableIR]]:
        classes: Dict[str, ClassIR] = {}
        tables: Dict[str, TableIR] = {}

        for path in paths:
            self._current_file = path
            tree = ET.parse(path)
            root = tree.getroot()
            self._walk(root, classes=classes, tables=tables)

        self._current_file = None
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

        base_path = getattr(element, "base", None)

        if tag.lower() in {"axclass", "class"}:
            class_ir = self._parse_class(element, current_model, current_package, path_hint=base_path)
            if class_ir:
                classes[class_ir.element_id()] = class_ir
            return

        if tag.lower() in {"axtable", "table"}:
            table_ir = self._parse_table(element, current_model, current_package)
            if table_ir:
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
        path_hint: Optional[str] = None,
    ) -> Optional[ClassIR]:
        name = element.attrib.get("Name") or element.attrib.get("name") or self._find_text(element, "Name")
        if not name:
            name = self._placeholder_name("Class")
            is_placeholder = True
        else:
            is_placeholder = False

        aot_path = element.attrib.get("Id") or element.attrib.get("Path") or path_hint or name
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
            is_placeholder=is_placeholder,
        )

        method_elements = element.findall(".//Methods/Method")
        if not method_elements:
            method_elements = element.findall(".//Method")
        if not method_elements:
            method_elements = element.findall(".//AxMethod")

        for method_element in method_elements:
            tag = _strip_namespace(method_element.tag).lower()
            if "method" not in tag:
                continue
            method_ir = self._parse_method(method_element, class_ir)
            if method_ir:
                class_ir.add_method(method_ir)

        return class_ir

    def _parse_method(self, element: ET.Element, class_ir: ClassIR) -> Optional[MethodIR]:
        name = (
            element.attrib.get("Name")
            or element.attrib.get("name")
            or self._find_text(element, "Name")
        )
        if not name:
            self._warn(f"Skipping method element missing name in class {class_ir.name}")
            return None

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
    ) -> Optional[TableIR]:
        name = element.attrib.get("Name") or element.attrib.get("name") or self._find_text(element, "Name")
        if not name:
            name = self._placeholder_name("Table")
            is_placeholder = True
        else:
            is_placeholder = False

        aot_path = element.attrib.get("Id") or element.attrib.get("Path") or name
        layer = element.attrib.get("Layer")

        table_ir = TableIR(
            name=name,
            aot_path=aot_path,
            model=model or "UNKNOWN",
            package=package,
            layer=layer,
            is_placeholder=is_placeholder,
        )

        fields_container = element.find(".//Fields")
        field_elements: list[ET.Element]
        if fields_container is not None:
            field_elements = list(fields_container)
        else:
            field_elements = element.findall(".//AxTableField")
            if not field_elements:
                field_elements = element.findall(".//Field")

        for field_element in field_elements:
            tag = _strip_namespace(field_element.tag).lower()
            if "field" not in tag:
                continue
            field_ir = self._parse_field(field_element, table_ir)
            if field_ir:
                table_ir.add_field(field_ir)

        return table_ir

    def _parse_field(self, element: ET.Element, table_ir: TableIR) -> Optional[FieldIR]:
        name = element.attrib.get("Name") or element.attrib.get("name") or self._find_text(element, "Name")
        if not name:
            name = self._placeholder_name("Field", suffix=table_ir.name)
            is_placeholder = True
        else:
            is_placeholder = False

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
            is_placeholder=is_placeholder,
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

    def _warn(self, message: str) -> None:
        location = str(self._current_file) if self._current_file else "unknown file"
        print(f"[parser] {message} ({location})")

    def _placeholder_name(self, prefix: str, suffix: str | None = None) -> str:
        base = prefix.strip() or "Unnamed"
        if suffix:
            base = f"{base}_{suffix}"
        if self._current_file:
            return f"{base}_{abs(hash(self._current_file)) & 0xFFFF}"
        return f"{base}_Placeholder"


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


