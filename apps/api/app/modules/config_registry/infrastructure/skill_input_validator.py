from __future__ import annotations

from typing import Any

from app.modules.config_registry.schemas.config_schemas import SchemaField


class SkillInputValidationError(ValueError):
    pass


def validate_input_schema(schema_map: dict[str, SchemaField], input_data: dict[str, Any]) -> None:
    for field_name, schema in schema_map.items():
        if field_name not in input_data:
            _validate_missing(field_name, schema)
            continue
        _validate_field(field_name, schema, input_data[field_name])


def _validate_missing(path: str, schema: SchemaField) -> None:
    if schema.required and schema.default is None:
        raise SkillInputValidationError(f"Required variable missing: {path}")


def _validate_field(path: str, schema: SchemaField, value: Any) -> None:
    _validate_type(path, schema.field_type, value)
    _validate_enum(path, schema, value)
    _validate_range(path, schema, value)
    _validate_length(path, schema, value)
    if schema.field_type == "array" and schema.items is not None:
        for index, item in enumerate(value):
            _validate_field(f"{path}[{index}]", schema.items, item)
    if schema.field_type == "object" and schema.properties:
        _validate_object(path, schema.properties, value)


def _validate_type(path: str, field_type: str, value: Any) -> None:
    type_checks = {
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "array": lambda item: isinstance(item, list),
        "object": lambda item: isinstance(item, dict),
    }
    if not type_checks[field_type](value):
        raise SkillInputValidationError(f"Invalid type for {path}: expected {field_type}")


def _validate_enum(path: str, schema: SchemaField, value: Any) -> None:
    if schema.enum and value not in schema.enum:
        raise SkillInputValidationError(f"Invalid value for {path}: expected one of {schema.enum}")


def _validate_range(path: str, schema: SchemaField, value: Any) -> None:
    if schema.field_type != "integer":
        return
    if schema.min is not None and value < schema.min:
        raise SkillInputValidationError(f"Invalid value for {path}: minimum is {schema.min}")
    if schema.max is not None and value > schema.max:
        raise SkillInputValidationError(f"Invalid value for {path}: maximum is {schema.max}")


def _validate_length(path: str, schema: SchemaField, value: Any) -> None:
    if not hasattr(value, "__len__"):
        return
    value_length = len(value)
    if schema.min_length is not None and value_length < schema.min_length:
        raise SkillInputValidationError(f"Invalid length for {path}: minimum is {schema.min_length}")
    if schema.max_length is not None and value_length > schema.max_length:
        raise SkillInputValidationError(f"Invalid length for {path}: maximum is {schema.max_length}")


def _validate_object(path: str, properties: dict[str, SchemaField], value: dict[str, Any]) -> None:
    for field_name, schema in properties.items():
        field_path = f"{path}.{field_name}"
        if field_name not in value:
            _validate_missing(field_path, schema)
            continue
        _validate_field(field_path, schema, value[field_name])
    extra_fields = sorted(set(value) - set(properties))
    if extra_fields:
        raise SkillInputValidationError(f"Unknown field: {path}.{extra_fields[0]}")
