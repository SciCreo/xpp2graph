"""
Intermediate Representation (IR) models for Codex AOTGraph.

The IR layer captures parsed data from Dynamics 365 F&O AOT XML exports before
they are persisted into the knowledge graph.
"""

from .models import (
    ClassIR,
    FieldAccessIR,
    FieldIR,
    MethodIR,
    TableIR,
    parse_element_id,
)

__all__ = [
    "ClassIR",
    "FieldAccessIR",
    "FieldIR",
    "MethodIR",
    "TableIR",
    "parse_element_id",
]


