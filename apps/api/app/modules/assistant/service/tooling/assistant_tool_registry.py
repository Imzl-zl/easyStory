from __future__ import annotations

from .assistant_tool_runtime_dto import AssistantToolDescriptor

PROJECT_READ_DOCUMENTS_MAX_PATHS = 8
PROJECT_EDIT_DOCUMENT_MAX_EDITS = 20
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
PROJECT_DOCUMENT_TEXT_EDIT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "old_text": {
            "type": "string",
            "minLength": 1,
            "description": "要替换的原文片段，必须能结合上下文锚点唯一定位。",
        },
        "new_text": {
            "type": "string",
            "description": "替换后的新文本；允许为空字符串表示删除。",
        },
        "context_before": {
            "anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}],
            "description": "紧邻 old_text 之前的原文锚点；old_text 多处命中时用于消歧。",
        },
        "context_after": {
            "anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}],
            "description": "紧邻 old_text 之后的原文锚点；old_text 多处命中时用于消歧。",
        },
    },
    "required": ["old_text", "new_text"],
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
                "description": f"要读取的统一项目文稿路径，一次最多 {PROJECT_READ_DOCUMENTS_MAX_PATHS} 份。",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
                "maxItems": PROJECT_READ_DOCUMENTS_MAX_PATHS,
            },
            "cursors": {
                "anyOf": [
                    {
                        "type": "array",
                        "description": "与 paths 按顺序一一对应的分页 cursor。",
                        "items": {"type": "string", "minLength": 1},
                        "maxItems": PROJECT_READ_DOCUMENTS_MAX_PATHS,
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
    description=(
        "基于 base_version 写回单份项目文稿的下一版完整全文。"
        "content 必须是修改后的完整文稿全文，不是新增片段、diff、patch 或局部替换。"
    ),
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "path": {"type": "string", "minLength": 1},
            "content": {
                "type": "string",
                "description": (
                    "修改后的完整文稿全文。不得只传新增段落、局部片段、diff、patch 或替换说明。"
                ),
            },
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

PROJECT_EDIT_DOCUMENT_DESCRIPTOR = AssistantToolDescriptor(
    name="project.edit_document",
    description=(
        "对当前授权的单份项目文稿执行确定性局部文本替换。"
        "每个 edit 使用 old_text 加可选的紧邻上下文锚点唯一定位；"
        "命中 0 处、多处或重叠时会失败，不做模糊匹配或猜测。"
    ),
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "path": {"type": "string", "minLength": 1},
            "edits": {
                "type": "array",
                "description": f"要原子应用的文本替换列表，一次最多 {PROJECT_EDIT_DOCUMENT_MAX_EDITS} 个。",
                "items": PROJECT_DOCUMENT_TEXT_EDIT_SCHEMA,
                "minItems": 1,
                "maxItems": PROJECT_EDIT_DOCUMENT_MAX_EDITS,
            },
            "base_version": {"type": "string", "minLength": 1},
        },
        "required": ["path", "edits", "base_version"],
    },
    output_schema=PROJECT_WRITE_DOCUMENT_DESCRIPTOR.output_schema,
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
            PROJECT_EDIT_DOCUMENT_DESCRIPTOR,
        ),
    ) -> None:
        self._descriptors = {item.name: item for item in descriptors}

    def list_descriptors(self) -> list[AssistantToolDescriptor]:
        return list(self._descriptors.values())

    def get_descriptor(self, tool_name: str) -> AssistantToolDescriptor | None:
        return self._descriptors.get(tool_name)
