from __future__ import annotations

from .assistant_tool_runtime_dto import AssistantToolDescriptor

PROJECT_DOCUMENT_SOURCES = ["file", "outline", "opening_plan", "chapter"]
PROJECT_DOCUMENT_CONTENT_STATES = ["ready", "empty", "placeholder"]
PROJECT_DOCUMENT_CATALOG_ENTRY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "path": {"type": "string", "minLength": 1},
        "document_ref": {"type": "string", "minLength": 1},
        "binding_version": {"type": "string", "minLength": 1},
        "resource_uri": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "source": {"type": "string", "enum": PROJECT_DOCUMENT_SOURCES},
        "document_kind": {"type": "string", "minLength": 1},
        "mime_type": {"type": "string", "minLength": 1},
        "schema_id": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]},
        "content_state": {"type": "string", "enum": PROJECT_DOCUMENT_CONTENT_STATES},
        "writable": {"type": "boolean"},
        "version": {"type": "string", "minLength": 1},
        "updated_at": {"anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]},
        "catalog_version": {"type": "string", "minLength": 1},
    },
    "required": [
        "path",
        "document_ref",
        "binding_version",
        "resource_uri",
        "title",
        "source",
        "document_kind",
        "mime_type",
        "schema_id",
        "content_state",
        "writable",
        "version",
        "updated_at",
        "catalog_version",
    ],
}
PROJECT_DOCUMENT_READ_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **PROJECT_DOCUMENT_CATALOG_ENTRY_SCHEMA["properties"],
        "content": {"type": "string"},
        "truncated": {"type": "boolean"},
        "next_cursor": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]},
    },
    "required": [
        *PROJECT_DOCUMENT_CATALOG_ENTRY_SCHEMA["required"],
        "content",
        "truncated",
        "next_cursor",
    ],
}
PROJECT_DOCUMENT_READ_ERROR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "path": {"type": "string", "minLength": 1},
        "code": {"type": "string", "minLength": 1},
        "message": {"type": "string", "minLength": 1},
    },
    "required": ["path", "code", "message"],
}
PROJECT_DOCUMENT_SEARCH_HIT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "path": {"type": "string", "minLength": 1},
        "document_ref": {"type": "string", "minLength": 1},
        "binding_version": {"type": "string", "minLength": 1},
        "resource_uri": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "source": {"type": "string", "enum": PROJECT_DOCUMENT_SOURCES},
        "document_kind": {"type": "string", "minLength": 1},
        "schema_id": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]},
        "content_state": {"type": "string", "enum": PROJECT_DOCUMENT_CONTENT_STATES},
        "writable": {"type": "boolean"},
        "version": {"type": "string", "minLength": 1},
        "updated_at": {"anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]},
        "matched_fields": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "path",
                    "title",
                    "schema_id",
                    "source",
                    "document_kind",
                    "content_state",
                ],
            },
        },
        "match_score": {"type": "integer", "minimum": 0},
    },
    "required": [
        "path",
        "document_ref",
        "binding_version",
        "resource_uri",
        "title",
        "source",
        "document_kind",
        "schema_id",
        "content_state",
        "writable",
        "version",
        "updated_at",
        "matched_fields",
        "match_score",
    ],
}
PROJECT_DOCUMENT_WRITE_DIFF_SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "changed": {"type": "boolean"},
        "previous_chars": {"type": "integer", "minimum": 0},
        "next_chars": {"type": "integer", "minimum": 0},
    },
    "required": ["changed", "previous_chars", "next_chars"],
}

PROJECT_LIST_DOCUMENTS_DESCRIPTOR = AssistantToolDescriptor(
    name="project.list_documents",
    description="列出当前项目目录中 assistant 可访问的文稿。",
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {},
    },
    output_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "documents": {
                "type": "array",
                "items": PROJECT_DOCUMENT_CATALOG_ENTRY_SCHEMA,
            },
            "catalog_version": {"type": "string", "minLength": 1},
        },
        "required": ["documents", "catalog_version"],
    },
    origin="project_document",
    trust_class="local_first_party",
    plane="resource",
    mutability="read_only",
    execution_locus="local_runtime",
    approval_mode="none",
    idempotency_class="safe_read",
    timeout_seconds=15,
    strict=True,
)

PROJECT_SEARCH_DOCUMENTS_DESCRIPTOR = AssistantToolDescriptor(
    name="project.search_documents",
    description="按路径名、标题与基础元数据检索当前项目中的文稿候选。",
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "path_prefix": {"type": "string", "minLength": 1},
            "sources": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": PROJECT_DOCUMENT_SOURCES,
                },
                "minItems": 1,
            },
            "schema_ids": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
            "content_states": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": PROJECT_DOCUMENT_CONTENT_STATES,
                },
                "minItems": 1,
            },
            "writable": {"type": "boolean"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "anyOf": [
            {"required": ["query"]},
            {"required": ["path_prefix"]},
            {"required": ["sources"]},
            {"required": ["schema_ids"]},
            {"required": ["content_states"]},
            {"required": ["writable"]},
        ],
    },
    output_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "documents": {
                "type": "array",
                "items": PROJECT_DOCUMENT_SEARCH_HIT_SCHEMA,
            },
            "catalog_version": {"type": "string", "minLength": 1},
        },
        "required": ["documents", "catalog_version"],
    },
    origin="project_document",
    trust_class="local_first_party",
    plane="resource",
    mutability="read_only",
    execution_locus="local_runtime",
    approval_mode="none",
    idempotency_class="safe_read",
    timeout_seconds=15,
    strict=True,
)

PROJECT_READ_DOCUMENTS_DESCRIPTOR = AssistantToolDescriptor(
    name="project.read_documents",
    description="读取当前项目目录中的一批文稿。",
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
            "cursors": {
                "anyOf": [
                    {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    {"type": "null"},
                ],
            },
        },
        "required": ["paths"],
    },
    output_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "documents": {
                "type": "array",
                "items": PROJECT_DOCUMENT_READ_ITEM_SCHEMA,
            },
            "errors": {
                "type": "array",
                "items": PROJECT_DOCUMENT_READ_ERROR_SCHEMA,
            },
            "catalog_version": {"type": "string", "minLength": 1},
        },
        "required": ["documents", "errors", "catalog_version"],
    },
    origin="project_document",
    trust_class="local_first_party",
    plane="resource",
    mutability="read_only",
    execution_locus="local_runtime",
    approval_mode="none",
    idempotency_class="safe_read",
    timeout_seconds=15,
    strict=True,
)

PROJECT_WRITE_DOCUMENT_DESCRIPTOR = AssistantToolDescriptor(
    name="project.write_document",
    description="写回当前项目目录中的单份文稿。",
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "path": {"type": "string", "minLength": 1},
            "content": {"type": "string"},
            "base_version": {"type": "string", "minLength": 1},
        },
        "required": ["path", "content", "base_version"],
    },
    output_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "path": {"type": "string", "minLength": 1},
            "document_ref": {"type": "string", "minLength": 1},
            "resource_uri": {"type": "string", "minLength": 1},
            "source": {"type": "string", "enum": PROJECT_DOCUMENT_SOURCES},
            "version": {"type": "string", "minLength": 1},
            "document_revision_id": {"type": "string", "minLength": 1},
            "updated_at": {"type": "string", "format": "date-time"},
            "diff_summary": PROJECT_DOCUMENT_WRITE_DIFF_SUMMARY_SCHEMA,
            "run_audit_id": {"type": "string", "minLength": 1},
        },
        "required": [
            "path",
            "document_ref",
            "resource_uri",
            "source",
            "version",
            "document_revision_id",
            "updated_at",
            "diff_summary",
            "run_audit_id",
        ],
    },
    origin="project_document",
    trust_class="local_first_party",
    plane="mutation",
    mutability="write",
    execution_locus="local_runtime",
    approval_mode="grant_bound",
    idempotency_class="conditional_write",
    timeout_seconds=30,
    strict=True,
)


class AssistantToolDescriptorRegistry:
    def __init__(
        self,
        *,
        descriptors: tuple[AssistantToolDescriptor, ...] = (
            PROJECT_LIST_DOCUMENTS_DESCRIPTOR,
            PROJECT_SEARCH_DOCUMENTS_DESCRIPTOR,
            PROJECT_READ_DOCUMENTS_DESCRIPTOR,
            PROJECT_WRITE_DOCUMENT_DESCRIPTOR,
        ),
    ) -> None:
        self._descriptors = {item.name: item for item in descriptors}

    def list_descriptors(self) -> list[AssistantToolDescriptor]:
        return list(self._descriptors.values())

    def get_descriptor(self, tool_name: str) -> AssistantToolDescriptor | None:
        return self._descriptors.get(tool_name)
