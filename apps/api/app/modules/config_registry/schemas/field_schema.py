from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .base_schema import StrictSchema


class SchemaField(StrictSchema):
    field_type: Literal["string", "integer", "boolean", "array", "object"] = Field(alias="type")
    required: bool = False
    description: str | None = None
    default: Any | None = None
    enum: list[Any] = Field(default_factory=list)
    min: int | float | None = None
    max: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    items: SchemaField | None = None
    properties: dict[str, SchemaField] = Field(default_factory=dict)


__all__ = ["SchemaField"]
