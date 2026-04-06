from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ProjectDocumentSchemaValidationError(ValueError):
    pass


SchemaValidator = Callable[[object], None]


def validate_project_document_schema(schema_id: str, payload: object) -> None:
    validator = SCHEMA_VALIDATORS.get(schema_id)
    if validator is None:
        return
    validator(payload)


def _validate_data_schema_document(payload: object) -> None:
    root = _require_object(payload, "结构定义文稿必须是 JSON 对象。")
    version = root.get("version")
    if not isinstance(version, int) or version <= 0:
        raise ProjectDocumentSchemaValidationError(
            "结构定义文稿必须包含正整数 version。"
        )
    collections = _require_object_field(root, "collections", "结构定义文稿必须包含对象 collections。")
    required_keys = (
        "characters",
        "factions",
        "character_relations",
        "faction_relations",
        "memberships",
        "events",
    )
    for key in required_keys:
        collection = _require_object_field(
            collections,
            key,
            f"结构定义文稿 collections.{key} 必须是对象。",
        )
        _require_non_empty_string_field(
            collection,
            "path",
            f"结构定义文稿 collections.{key}.path 必须是非空字符串。",
        )
        _require_non_empty_string_field(
            collection,
            "primary_key",
            f"结构定义文稿 collections.{key}.primary_key 必须是非空字符串。",
        )


def _validate_characters_document(payload: object) -> None:
    _validate_collection_items(
        payload,
        collection_key="characters",
        required_fields=("id", "name", "role", "status"),
    )


def _validate_factions_document(payload: object) -> None:
    _validate_collection_items(
        payload,
        collection_key="factions",
        required_fields=("id", "name"),
    )


def _validate_character_relations_document(payload: object) -> None:
    _validate_collection_items(
        payload,
        collection_key="character_relations",
        required_fields=("id", "source", "target"),
    )


def _validate_faction_relations_document(payload: object) -> None:
    _validate_collection_items(
        payload,
        collection_key="faction_relations",
        required_fields=("id", "source", "target"),
    )


def _validate_memberships_document(payload: object) -> None:
    _validate_collection_items(
        payload,
        collection_key="memberships",
        required_fields=("id", "character_id", "faction_id"),
    )


def _validate_events_document(payload: object) -> None:
    _validate_collection_items(
        payload,
        collection_key="events",
        required_fields=("id", "title"),
    )


def _validate_collection_items(
    payload: object,
    *,
    collection_key: str,
    required_fields: tuple[str, ...],
) -> None:
    root = _require_object(payload, "目标数据文稿必须是 JSON 对象。")
    items = root.get(collection_key)
    if not isinstance(items, list):
        raise ProjectDocumentSchemaValidationError(
            f"目标数据文稿必须包含数组字段 {collection_key}。"
        )
    for index, item in enumerate(items):
        item_object = _require_object(
            item,
            f"目标数据文稿 {collection_key}[{index}] 必须是对象。",
        )
        for field_name in required_fields:
            _require_non_empty_string_field(
                item_object,
                field_name,
                f"目标数据文稿 {collection_key}[{index}].{field_name} 必须是非空字符串。",
            )


def _require_object(payload: object, message: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    raise ProjectDocumentSchemaValidationError(message)


def _require_object_field(
    payload: dict[str, Any],
    field_name: str,
    message: str,
) -> dict[str, Any]:
    return _require_object(payload.get(field_name), message)


def _require_non_empty_string_field(
    payload: dict[str, Any],
    field_name: str,
    message: str,
) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    raise ProjectDocumentSchemaValidationError(message)


SCHEMA_VALIDATORS: dict[str, SchemaValidator] = {
    "project.data_schema": _validate_data_schema_document,
    "project.characters": _validate_characters_document,
    "project.factions": _validate_factions_document,
    "project.character_relations": _validate_character_relations_document,
    "project.faction_relations": _validate_faction_relations_document,
    "project.memberships": _validate_memberships_document,
    "project.events": _validate_events_document,
}
