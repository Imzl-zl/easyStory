from __future__ import annotations

from .assistant_tool_policy_resolver import AssistantToolPolicyResolver
from .assistant_tool_registry import AssistantToolDescriptorRegistry
from .assistant_tool_runtime_dto import (
    AssistantToolDescriptor,
    AssistantToolExposureContext,
    AssistantToolPolicyDecision,
)


class AssistantToolExposurePolicy:
    def __init__(
        self,
        *,
        registry: AssistantToolDescriptorRegistry,
        resolver: AssistantToolPolicyResolver | None = None,
    ) -> None:
        self.registry = registry
        self.resolver = resolver or AssistantToolPolicyResolver()

    def resolve_visible_tools(
        self,
        *,
        context: AssistantToolExposureContext,
    ) -> list[AssistantToolDescriptor]:
        return [
            item.descriptor
            for item in self.resolve_policy_decisions(context=context)
            if item.visibility == "visible"
        ]

    def resolve_policy_decisions(
        self,
        *,
        context: AssistantToolExposureContext,
    ) -> list[AssistantToolPolicyDecision]:
        return [
            self.resolver.resolve(
                descriptor=descriptor,
                context=context,
            )
            for descriptor in self.registry.list_descriptors()
        ]
