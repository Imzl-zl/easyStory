from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.runtime.llm.llm_protocol_types import LLMContinuationSupport
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse

from ..assistant_run_budget import AssistantRunBudget, build_assistant_run_budget
from .assistant_tool_exposure_policy import AssistantToolExposurePolicy
from .assistant_tool_executor import AssistantToolExecutor
from .assistant_tool_loop_context_support import (
    _build_tool_execution_context,
    _build_tool_exposure_context,
)
from .assistant_tool_loop_plan_support import (
    _build_policy_decision_by_name,
)
from .assistant_tool_loop_result_support import (
    _coerce_recoverable_tool_error,
    _execute_tool_call_with_timeout,
)
from .assistant_tool_loop_runtime import (
    AssistantToolLoopIterationItem,
    AssistantToolLoopModelStreamEvent,
    AssistantToolLoopRuntime,
    ToolModelCaller,
    ToolStreamModelCaller,
)
from .assistant_tool_loop_runtime_support import raise_if_cancelled
from .assistant_tool_loop_step_support import (
    _build_cancelled_tool_step_record,
    _build_completed_tool_step_record,
    _build_failed_tool_step_record,
    _build_progress_tool_step_record,
    _build_started_tool_step_record,
    _build_tool_state_persist_error,
)
from .assistant_tool_runtime_dto import (
    AssistantToolDescriptor,
    AssistantToolLoopStateRecorder,
    AssistantToolPolicyDecision,
    AssistantToolResultEnvelope,
)
from .assistant_tool_step_store import AssistantToolStepRecord, AssistantToolStepStore

if TYPE_CHECKING:
    from ..turn.assistant_turn_runtime_support import AssistantTurnContext


DEFAULT_ASSISTANT_TOOL_LOOP_MAX_ITERATIONS = 8


@dataclass(frozen=True)
class AssistantToolLoopResult:
    raw_output: LLMGenerateToolResponse


class AssistantToolLoop:
    def __init__(
        self,
        *,
        exposure_policy: AssistantToolExposurePolicy,
        executor: AssistantToolExecutor,
        step_store: AssistantToolStepStore | None = None,
        max_iterations: int = DEFAULT_ASSISTANT_TOOL_LOOP_MAX_ITERATIONS,
    ) -> None:
        self.exposure_policy = exposure_policy
        self.executor = executor
        self.step_store = step_store
        if max_iterations < 1:
            raise ConfigurationError("Assistant tool loop max_iterations must be >= 1")
        self.max_iterations = max_iterations

    async def execute(
        self,
        db: AsyncSession,
        *,
        turn_context: "AssistantTurnContext",
        owner_id: Any,
        project_id: Any,
        prompt: str,
        system_prompt: str | None,
        continuation_support: LLMContinuationSupport,
        model_caller: ToolModelCaller,
        run_budget: AssistantRunBudget | None = None,
        tool_policy_decisions: tuple[AssistantToolPolicyDecision, ...] | None = None,
        visible_descriptors: tuple[AssistantToolDescriptor, ...] | None = None,
        state_recorder: AssistantToolLoopStateRecorder | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AssistantToolLoopResult:
        async for item in self.iterate(
            db,
            turn_context=turn_context,
            owner_id=owner_id,
            project_id=project_id,
            prompt=prompt,
            system_prompt=system_prompt,
            continuation_support=continuation_support,
            model_caller=model_caller,
            run_budget=run_budget,
            tool_policy_decisions=tool_policy_decisions,
            visible_descriptors=visible_descriptors,
            state_recorder=state_recorder,
            should_stop=should_stop,
        ):
            if item.raw_output is not None:
                return AssistantToolLoopResult(raw_output=item.raw_output)
        raise ConfigurationError("Assistant tool loop exited without final output")

    def resolve_tool_schemas(
        self,
        *,
        turn_context: "AssistantTurnContext",
        project_id: Any,
        visible_descriptors: tuple[AssistantToolDescriptor, ...] | None = None,
    ) -> list[dict[str, Any]]:
        visible_tools = list(visible_descriptors or self.resolve_visible_descriptors(
            turn_context=turn_context,
            project_id=project_id,
        ))
        return [_serialize_tool_schema(item) for item in visible_tools]

    def resolve_policy_decisions(
        self,
        *,
        turn_context: "AssistantTurnContext",
        project_id: Any,
        budget_snapshot: dict[str, Any] | None = None,
    ) -> list[AssistantToolPolicyDecision]:
        return self.exposure_policy.resolve_policy_decisions(
            context=_build_tool_exposure_context(
                turn_context=turn_context,
                project_id=project_id,
                budget_snapshot=budget_snapshot,
            )
        )

    def resolve_policy_bundle(
        self,
        *,
        turn_context: "AssistantTurnContext",
        project_id: Any,
    ) -> tuple[tuple[AssistantToolPolicyDecision, ...], tuple[AssistantToolDescriptor, ...], AssistantRunBudget]:
        preliminary_decisions = tuple(
            self.resolve_policy_decisions(
                turn_context=turn_context,
                project_id=project_id,
            )
        )
        preliminary_visible = tuple(
            item.descriptor
            for item in preliminary_decisions
            if item.visibility == "visible"
        )
        budget = build_assistant_run_budget(
            max_steps=self.max_iterations,
            visible_descriptors=preliminary_visible,
        )
        final_decisions = tuple(
            self.resolve_policy_decisions(
                turn_context=turn_context,
                project_id=project_id,
                budget_snapshot=budget.model_dump(),
            )
        )
        final_visible = tuple(
            item.descriptor
            for item in final_decisions
            if item.visibility == "visible"
        )
        final_budget = build_assistant_run_budget(
            max_steps=self.max_iterations,
            visible_descriptors=final_visible,
        )
        if final_budget != budget:
            raise ConfigurationError(
                "Assistant tool policy resolution must not change visible tools after budget_snapshot is applied"
            )
        return final_decisions, final_visible, final_budget

    def resolve_visible_descriptors(
        self,
        *,
        turn_context: "AssistantTurnContext",
        project_id: Any,
    ) -> list[AssistantToolDescriptor]:
        return [
            item.descriptor
            for item in self.resolve_policy_decisions(
                turn_context=turn_context,
                project_id=project_id,
            )
            if item.visibility == "visible"
        ]

    def resolve_run_budget(
        self,
        *,
        turn_context: "AssistantTurnContext",
        project_id: Any,
        visible_descriptors: tuple[AssistantToolDescriptor, ...] | None = None,
    ) -> AssistantRunBudget:
        visible_tools = tuple(
            visible_descriptors or self.resolve_visible_descriptors(
                turn_context=turn_context,
                project_id=project_id,
            )
        )
        return build_assistant_run_budget(
            max_steps=self.max_iterations,
            visible_descriptors=visible_tools,
        )

    async def iterate(
        self,
        db: AsyncSession,
        *,
        turn_context: "AssistantTurnContext",
        owner_id: Any,
        project_id: Any,
        prompt: str,
        system_prompt: str | None,
        continuation_support: LLMContinuationSupport,
        model_caller: ToolModelCaller,
        stream_model_caller: ToolStreamModelCaller | None = None,
        initial_raw_output: LLMGenerateToolResponse | None = None,
        run_budget: AssistantRunBudget | None = None,
        tool_policy_decisions: tuple[AssistantToolPolicyDecision, ...] | None = None,
        visible_descriptors: tuple[AssistantToolDescriptor, ...] | None = None,
        state_recorder: AssistantToolLoopStateRecorder | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[AssistantToolLoopIterationItem]:
        tool_schemas = self.resolve_tool_schemas(
            turn_context=turn_context,
            project_id=project_id,
            visible_descriptors=visible_descriptors,
        )
        resolved_run_budget = run_budget or self.resolve_run_budget(
            turn_context=turn_context,
            project_id=project_id,
            visible_descriptors=visible_descriptors,
        )
        resolved_policy_decisions = tuple(
            tool_policy_decisions
            or self.resolve_policy_decisions(
                turn_context=turn_context,
                project_id=project_id,
                budget_snapshot=resolved_run_budget.model_dump(),
            )
        )
        policy_decision_by_name = _build_policy_decision_by_name(resolved_policy_decisions)
        runtime = AssistantToolLoopRuntime(
            tool_loop=self,
            db=db,
            turn_context=turn_context,
            owner_id=owner_id,
            project_id=project_id,
            prompt=prompt,
            system_prompt=system_prompt,
            continuation_support=continuation_support,
            model_caller=model_caller,
            stream_model_caller=stream_model_caller,
            initial_raw_output=initial_raw_output,
            run_budget=resolved_run_budget,
            tool_schemas=tool_schemas,
            policy_decision_by_name=policy_decision_by_name,
            state_recorder=state_recorder,
            should_stop=should_stop,
        )
        async for item in runtime.iterate():
            yield item

    async def _execute_single_tool_call(
        self,
        db: AsyncSession,
        *,
        step_index: int,
        turn_context: "AssistantTurnContext",
        owner_id: Any,
        project_id: Any,
        tool_call: dict[str, Any],
        descriptor: AssistantToolDescriptor | None = None,
        tool_policy_decision: AssistantToolPolicyDecision | None,
        should_stop: Callable[[], Awaitable[bool]] | None,
    ) -> AssistantToolResultEnvelope:
        resolved_descriptor = (
            descriptor
            if descriptor is not None
            else (
                tool_policy_decision.descriptor
                if tool_policy_decision is not None
                else self._require_tool_descriptor(str(tool_call["tool_name"]))
            )
        )
        execution_context = _build_tool_execution_context(
            turn_context=turn_context,
            owner_id=owner_id,
            project_id=project_id,
            tool_call=tool_call,
            descriptor=resolved_descriptor,
            tool_policy_decision=tool_policy_decision,
        )
        started_at = datetime.now(UTC)
        self._append_step_snapshot(
            _build_started_tool_step_record(
                context=execution_context,
                descriptor=resolved_descriptor,
                step_index=step_index,
                started_at=started_at,
            )
        )
        try:
            await raise_if_cancelled(should_stop)
        except StreamInterruptedError:
            self._append_step_snapshot(
                _build_cancelled_tool_step_record(
                    context=execution_context,
                    descriptor=resolved_descriptor,
                    step_index=step_index,
                    started_at=started_at,
                )
            )
            raise
        try:
            arguments_error = _read_tool_call_arguments_error(tool_call)
            if arguments_error is not None:
                raise ValueError(arguments_error)
            result = await _execute_tool_call_with_timeout(
                db=db,
                executor=self.executor,
                context=execution_context,
                descriptor=resolved_descriptor,
                on_lifecycle_update=lambda update: self._append_step_snapshot(
                    _build_progress_tool_step_record(
                        context=execution_context,
                        descriptor=resolved_descriptor,
                        step_index=step_index,
                        started_at=started_at,
                        update=update,
                    )
                ),
            )
        except Exception as exc:
            recoverable_result = _coerce_recoverable_tool_error(
                context=execution_context,
                error=exc,
            )
            if recoverable_result is None:
                self._append_step_snapshot(
                    _build_failed_tool_step_record(
                        context=execution_context,
                        descriptor=resolved_descriptor,
                        step_index=step_index,
                        started_at=started_at,
                        error=exc,
                    )
                )
                raise
            result = recoverable_result
        completed_record = _build_completed_tool_step_record(
            context=execution_context,
            descriptor=resolved_descriptor,
            step_index=step_index,
            started_at=started_at,
            result=result,
        )
        try:
            self._append_step_snapshot(completed_record)
        except Exception as exc:
            raise _build_tool_state_persist_error(
                descriptor=resolved_descriptor,
                result=result,
                cause=exc,
            ) from exc
        return result

    def _require_tool_descriptor(self, tool_name: str) -> AssistantToolDescriptor:
        descriptor = self.exposure_policy.registry.get_descriptor(tool_name)
        if descriptor is None:
            raise ConfigurationError(f"Unknown assistant tool descriptor: {tool_name}")
        return descriptor

    def _append_step_snapshot(self, record: AssistantToolStepRecord) -> None:
        if self.step_store is None:
            return
        self.step_store.append_step(record)


__all__ = [
    "AssistantToolLoop",
    "AssistantToolLoopIterationItem",
    "AssistantToolLoopModelStreamEvent",
    "AssistantToolLoopResult",
]


def _serialize_tool_schema(descriptor: AssistantToolDescriptor) -> dict[str, Any]:
    return {
        "name": descriptor.name,
        "description": descriptor.description,
        "parameters": descriptor.input_schema,
        "strict": descriptor.strict,
    }


def _read_optional_tool_call_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _read_tool_call_arguments_error(tool_call: dict[str, Any]) -> str | None:
    return _read_optional_tool_call_string(tool_call.get("arguments_error"))
