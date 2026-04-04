from __future__ import annotations

from .assistant_tool_registry import AssistantToolDescriptorRegistry
from .assistant_tool_runtime_dto import AssistantToolDescriptor, AssistantToolExposureContext


class AssistantToolExposurePolicy:
    def __init__(self, *, registry: AssistantToolDescriptorRegistry) -> None:
        self.registry = registry

    def resolve_visible_tools(
        self,
        *,
        context: AssistantToolExposureContext,
    ) -> list[AssistantToolDescriptor]:
        if context.project_id is None:
            return []
        return [
            descriptor
            for descriptor in self.registry.list_descriptors()
            if descriptor.approval_mode in {"none", "grant_bound"}
        ]
