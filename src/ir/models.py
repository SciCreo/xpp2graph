"""
IR model definitions for Codex AOTGraph.

These dataclasses represent the structured, language-agnostic intermediate
representation produced after parsing Dynamics 365 F&O AOT XML exports.
The IR is intentionally explicit about unique identifiers and the metadata
needed by the downstream Neo4j loader layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple


class AccessModifier(str, Enum):
    """Supported method access modifiers captured from AOT metadata."""

    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    INTERNAL = "internal"


class FieldAccessType(str, Enum):
    """Represents whether a field access is a read or write in the call graph."""

    READ = "read"
    WRITE = "write"


def parse_element_id(model_name: str, *segments: str) -> str:
    """
    Construct a stable synthetic identifier for AOT elements.

    Args:
        model_name: Logical model or package name the element belongs to.
        *segments: Remaining segments in the AOT path (e.g. table, field, method).

    Returns:
        Canonical identifier string.
    """

    normalized = [model_name.strip()]
    normalized.extend(segment.strip() for segment in segments if segment)
    return "/".join(normalized)


@dataclass(slots=True)
class MethodIR:
    """
    Representation of an x++ method extracted from the AOT.

    The `aot_path` should align with the source XML path so repeated imports can
    reuse the same identifier. Parsing logic is expected to populate
    `called_methods` and `field_accesses` using lightweight static analysis.
    """

    name: str
    aot_path: str
    model: str
    class_name: str
    access: AccessModifier
    is_static: bool
    line_count: Optional[int] = None
    body: Optional[str] = None
    called_methods: List[str] = field(default_factory=list)
    field_accesses: List["FieldAccessIR"] = field(default_factory=list)

    def element_id(self) -> str:
        """Return the canonical ID used in the Neo4j graph."""

        return parse_element_id(self.model, self.class_name, self.name)


@dataclass(slots=True)
class FieldIR:
    """Representation of a table field defined in the AOT."""

    name: str
    aot_path: str
    table_name: str
    model: str
    extended_data_type: Optional[str] = None
    field_type: Optional[str] = None

    def element_id(self) -> str:
        return parse_element_id(self.model, self.table_name, self.name)


@dataclass(slots=True)
class TableIR:
    """Representation of a table node as exported from the AOT."""

    name: str
    aot_path: str
    model: str
    package: Optional[str] = None
    layer: Optional[str] = None
    fields: Dict[str, FieldIR] = field(default_factory=dict)

    def element_id(self) -> str:
        return parse_element_id(self.model, self.name)

    def add_field(self, field_ir: FieldIR) -> None:
        self.fields[field_ir.name] = field_ir


@dataclass(slots=True)
class ClassIR:
    """Representation of a class definition with associated methods."""

    name: str
    aot_path: str
    model: str
    package: Optional[str] = None
    layer: Optional[str] = None
    base_class: Optional[str] = None
    implements: Tuple[str, ...] = ()
    methods: Dict[str, MethodIR] = field(default_factory=dict)

    def element_id(self) -> str:
        return parse_element_id(self.model, self.name)

    def add_method(self, method_ir: MethodIR) -> None:
        self.methods[method_ir.name] = method_ir


@dataclass(slots=True)
class FieldAccessIR:
    """
    Captures a single field access within a method body.

    The Neo4j loader will convert these entries into `[:READS_FIELD]` or
    `[:WRITES_FIELD]` edges based on the `access_type` attribute.
    """

    table_name: str
    field_name: str
    model: str
    access_type: FieldAccessType

    def target_field_id(self) -> str:
        return parse_element_id(self.model, self.table_name, self.field_name)


IRRegistry = Dict[str, ClassIR]


def iter_methods(classes: Iterable[ClassIR]) -> Iterable[MethodIR]:
    """Yield all methods contained within a collection of classes."""

    for class_ir in classes:
        yield from class_ir.methods.values()


def iter_fields(tables: Iterable[TableIR]) -> Iterable[FieldIR]:
    """Yield all fields contained within a collection of tables."""

    for table_ir in tables:
        yield from table_ir.fields.values()


