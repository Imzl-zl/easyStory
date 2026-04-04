from __future__ import annotations

from .assistant_tool_runtime_dto import AssistantToolDescriptor

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
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
        },
        "required": ["paths"],
    },
    output_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "documents": {"type": "array"},
            "errors": {"type": "array"},
            "catalog_version": {"type": "string"},
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
)


class AssistantToolDescriptorRegistry:
    def __init__(
        self,
        *,
        descriptors: tuple[AssistantToolDescriptor, ...] = (PROJECT_READ_DOCUMENTS_DESCRIPTOR,),
    ) -> None:
        self._descriptors = {item.name: item for item in descriptors}

    def list_descriptors(self) -> list[AssistantToolDescriptor]:
        return list(self._descriptors.values())

    def get_descriptor(self, tool_name: str) -> AssistantToolDescriptor | None:
        return self._descriptors.get(tool_name)
