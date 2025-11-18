"""
Pydantic models for Codex AOTGraph API responses.
"""

from __future__ import annotations

from pydantic import BaseModel


class MethodRef(BaseModel):
    id: str
    name: str
    className: str
    model: str


class FieldRef(BaseModel):
    id: str
    name: str
    tableName: str
    model: str


class ClassRef(BaseModel):
    id: str
    name: str
    model: str


class ClassHierarchy(BaseModel):
    id: str
    name: str
    model: str
    baseClasses: list[ClassRef]


class WhereUsedResponse(BaseModel):
    target: MethodRef
    callers: list[MethodRef]


class FieldAccessResponse(BaseModel):
    field: FieldRef
    readers: list[MethodRef]
    writers: list[MethodRef]


