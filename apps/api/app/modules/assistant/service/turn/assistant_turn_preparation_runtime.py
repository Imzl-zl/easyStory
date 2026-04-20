from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError

from .assistant_turn_runtime_support import PreparedAssistantTurn


class LangGraphAssistantTurnPreparationRuntime:
    def __init__(
        self,
        *,
        resolve_scope_and_normalize: Callable[[], Awaitable[tuple[Any, Any, Any]]],
        validate_anchor: Callable[[Any, Any], None],
        resolve_spec_and_rules: Callable[[Any, Any], Awaitable[tuple[Any, Any, str | None]]],
        build_provisional_context: Callable[[Any, Any, Any, Any, Any], tuple[Any, Any, Any]],
        resolve_runtime_and_projection: Callable[
            [Any, Any, Any, Any, Any, str | None, Any, Any, Any],
            Awaitable[tuple[Any, Any, Any, Any, Any, Any, Any]],
        ],
        build_prepared_turn: Callable[[dict[str, Any]], PreparedAssistantTurn],
    ) -> None:
        self.resolve_scope_and_normalize = resolve_scope_and_normalize
        self.validate_anchor = validate_anchor
        self.resolve_spec_and_rules = resolve_spec_and_rules
        self.build_provisional_context = build_provisional_context
        self.resolve_runtime_and_projection = resolve_runtime_and_projection
        self.build_prepared_turn = build_prepared_turn

    async def run(self) -> PreparedAssistantTurn:
        project_id, normalized_turn_payload, normalized_payload = await self.resolve_scope_and_normalize()
        self.validate_anchor(project_id, normalized_payload)
        spec, rule_bundle, system_prompt = await self.resolve_spec_and_rules(
            project_id,
            normalized_payload,
        )
        (
            document_context_recovery_snapshot,
            document_context_injection_snapshot,
            provisional_turn_context,
        ) = self.build_provisional_context(
            project_id,
            normalized_turn_payload,
            normalized_payload,
            spec,
            rule_bundle,
        )
        (
            tool_policy_decisions,
            visible_tool_descriptors,
            run_budget,
            resolved_llm_runtime,
            tool_guidance_snapshot,
            prompt_projection,
            tool_catalog_version,
        ) = await self.resolve_runtime_and_projection(
            project_id,
            normalized_turn_payload,
            normalized_payload,
            spec,
            rule_bundle,
            system_prompt,
            provisional_turn_context,
            document_context_recovery_snapshot,
            document_context_injection_snapshot,
        )
        prepared_turn = self.build_prepared_turn(
            {
                "project_id": project_id,
                "normalized_turn_payload": normalized_turn_payload,
                "normalized_payload": normalized_payload,
                "spec": spec,
                "rule_bundle": rule_bundle,
                "system_prompt": system_prompt,
                "document_context_recovery_snapshot": document_context_recovery_snapshot,
                "document_context_injection_snapshot": document_context_injection_snapshot,
                "provisional_turn_context": provisional_turn_context,
                "tool_policy_decisions": tool_policy_decisions,
                "visible_tool_descriptors": visible_tool_descriptors,
                "run_budget": run_budget,
                "resolved_llm_runtime": resolved_llm_runtime,
                "tool_guidance_snapshot": tool_guidance_snapshot,
                "prompt_projection": prompt_projection,
                "tool_catalog_version": tool_catalog_version,
            }
        )
        if prepared_turn is None:
            raise ConfigurationError("Assistant turn preparation runtime completed without prepared turn")
        return prepared_turn
