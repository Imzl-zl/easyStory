from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError

from .assistant_turn_runtime_support import PreparedAssistantTurn


class AssistantTurnPreparationGraphState(TypedDict, total=False):
    project_id: Any
    normalized_turn_payload: Any
    normalized_payload: Any
    spec: Any
    rule_bundle: Any
    system_prompt: str | None
    document_context_recovery_snapshot: dict[str, Any] | None
    document_context_injection_snapshot: dict[str, Any] | None
    provisional_turn_context: Any
    tool_policy_decisions: tuple[Any, ...]
    visible_tool_descriptors: tuple[Any, ...]
    run_budget: Any
    resolved_llm_runtime: Any
    tool_guidance_snapshot: dict[str, Any] | None
    prompt_projection: Any
    tool_catalog_version: str | None
    prepared_turn: PreparedAssistantTurn


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
        build_prepared_turn: Callable[
            [dict[str, Any]],
            PreparedAssistantTurn,
        ],
    ) -> None:
        self.resolve_scope_and_normalize = resolve_scope_and_normalize
        self.validate_anchor = validate_anchor
        self.resolve_spec_and_rules = resolve_spec_and_rules
        self.build_provisional_context = build_provisional_context
        self.resolve_runtime_and_projection = resolve_runtime_and_projection
        self.build_prepared_turn = build_prepared_turn
        self._graph = self._build_graph()

    async def run(self) -> PreparedAssistantTurn:
        final_state = await self._graph.ainvoke({})
        prepared_turn = final_state.get("prepared_turn")
        if prepared_turn is None:
            raise ConfigurationError("Assistant turn preparation runtime completed without prepared turn")
        return prepared_turn

    def _build_graph(self):
        graph = StateGraph(AssistantTurnPreparationGraphState)
        graph.add_node("resolve_scope_and_normalize", self._resolve_scope_and_normalize)
        graph.add_node("validate_anchor", self._validate_anchor)
        graph.add_node("resolve_spec_and_rules", self._resolve_spec_and_rules)
        graph.add_node("build_provisional_context", self._build_provisional_context)
        graph.add_node("resolve_runtime_and_projection", self._resolve_runtime_and_projection)
        graph.add_node("build_prepared_turn", self._build_prepared_turn)
        graph.add_edge(START, "resolve_scope_and_normalize")
        graph.add_edge("resolve_scope_and_normalize", "validate_anchor")
        graph.add_edge("validate_anchor", "resolve_spec_and_rules")
        graph.add_edge("resolve_spec_and_rules", "build_provisional_context")
        graph.add_edge("build_provisional_context", "resolve_runtime_and_projection")
        graph.add_edge("resolve_runtime_and_projection", "build_prepared_turn")
        graph.add_edge("build_prepared_turn", END)
        return graph.compile(name="assistant_turn_preparation_runtime")

    async def _resolve_scope_and_normalize(
        self,
        _state: AssistantTurnPreparationGraphState,
    ) -> AssistantTurnPreparationGraphState:
        project_id, normalized_turn_payload, normalized_payload = await self.resolve_scope_and_normalize()
        return {
            "project_id": project_id,
            "normalized_turn_payload": normalized_turn_payload,
            "normalized_payload": normalized_payload,
        }

    def _validate_anchor(
        self,
        state: AssistantTurnPreparationGraphState,
    ) -> AssistantTurnPreparationGraphState:
        self.validate_anchor(
            state.get("project_id"),
            state.get("normalized_payload"),
        )
        return {}

    async def _resolve_spec_and_rules(
        self,
        state: AssistantTurnPreparationGraphState,
    ) -> AssistantTurnPreparationGraphState:
        project_id = state.get("project_id")
        normalized_payload = state.get("normalized_payload")
        spec, rule_bundle, system_prompt = await self.resolve_spec_and_rules(
            project_id,
            normalized_payload,
        )
        return {
            "spec": spec,
            "rule_bundle": rule_bundle,
            "system_prompt": system_prompt,
        }

    def _build_provisional_context(
        self,
        state: AssistantTurnPreparationGraphState,
    ) -> AssistantTurnPreparationGraphState:
        (
            document_context_recovery_snapshot,
            document_context_injection_snapshot,
            provisional_turn_context,
        ) = self.build_provisional_context(
            state.get("project_id"),
            state.get("normalized_turn_payload"),
            state.get("normalized_payload"),
            state.get("spec"),
            state.get("rule_bundle"),
        )
        return {
            "document_context_recovery_snapshot": document_context_recovery_snapshot,
            "document_context_injection_snapshot": document_context_injection_snapshot,
            "provisional_turn_context": provisional_turn_context,
        }

    async def _resolve_runtime_and_projection(
        self,
        state: AssistantTurnPreparationGraphState,
    ) -> AssistantTurnPreparationGraphState:
        (
            tool_policy_decisions,
            visible_tool_descriptors,
            run_budget,
            resolved_llm_runtime,
            tool_guidance_snapshot,
            prompt_projection,
            tool_catalog_version,
        ) = await self.resolve_runtime_and_projection(
            state.get("project_id"),
            state.get("normalized_turn_payload"),
            state.get("normalized_payload"),
            state.get("spec"),
            state.get("rule_bundle"),
            state.get("system_prompt"),
            state.get("provisional_turn_context"),
            state.get("document_context_recovery_snapshot"),
            state.get("document_context_injection_snapshot"),
        )
        return {
            "tool_policy_decisions": tool_policy_decisions,
            "visible_tool_descriptors": visible_tool_descriptors,
            "run_budget": run_budget,
            "resolved_llm_runtime": resolved_llm_runtime,
            "tool_guidance_snapshot": tool_guidance_snapshot,
            "prompt_projection": prompt_projection,
            "tool_catalog_version": tool_catalog_version,
        }

    def _build_prepared_turn(
        self,
        state: AssistantTurnPreparationGraphState,
    ) -> AssistantTurnPreparationGraphState:
        return {
            "prepared_turn": self.build_prepared_turn(dict(state)),
        }
