from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.runtime.llm_protocol import LLMContinuationSupport
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.provider_interop_stream_support import StreamInterruptedError

from .assistant_run_budget import AssistantRunBudget, build_assistant_run_budget
from .assistant_runtime_terminal import (
    AssistantRuntimeTerminalError,
    build_cancel_requested_terminal_error,
)
from .assistant_tool_exposure_policy import AssistantToolExposurePolicy
from .assistant_tool_executor import AssistantToolExecutor
from .assistant_tool_loop_context_support import (
    _build_pending_tool_calls_snapshot,
    _build_tool_execution_context,
    _build_tool_exposure_context,
    _record_tool_loop_state,
)
from .assistant_tool_loop_budget_support import apply_tool_loop_request_budget
from .assistant_tool_loop_output_support import (
    _UsageTotals,
    _append_intermediate_text_item,
    _build_final_response_normalized_input_items,
    _build_final_output,
    _build_tool_cycle_normalized_input_items,
    _build_tool_cycle_continuation_items,
    _build_tool_cycle_output_items,
    _merge_usage_totals,
    _resolve_provider_continuation_state,
)
from .assistant_tool_loop_plan_support import (
    _build_policy_decision_by_name,
    _plan_tool_cycle_calls,
)
from .assistant_tool_loop_result_support import (
    AssistantToolStatePersistError,
    _build_cancelled_tool_call_result_payload,
    _coerce_recoverable_tool_error,
    _build_failed_tool_call_result_payload,
    _build_state_persist_failed_tool_call_result_payload,
    _build_tool_call_result_payload,
    _build_tool_call_start_payload,
    _execute_tool_call_with_timeout,
    _tool_result_committed_write,
)
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
    from .assistant_turn_runtime_support import AssistantTurnContext


ToolModelCaller = Callable[..., Awaitable[dict[str, Any]]]
ToolStreamModelCaller = Callable[..., AsyncIterator["AssistantToolLoopModelStreamEvent"]]
DEFAULT_ASSISTANT_TOOL_LOOP_MAX_ITERATIONS = 8


@dataclass(frozen=True)
class AssistantToolLoopResult:
    raw_output: dict[str, Any]


@dataclass(frozen=True)
class AssistantToolLoopIterationItem:
    event_name: str | None = None
    event_payload: dict[str, Any] | None = None
    raw_output: dict[str, Any] | None = None
    raw_output_already_streamed: bool = False


@dataclass(frozen=True)
class AssistantToolLoopModelStreamEvent:
    delta: str | None = None
    raw_output: dict[str, Any] | None = None


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
        initial_raw_output: dict[str, Any] | None = None,
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
        if not tool_schemas:
            await _raise_if_cancelled(should_stop)
            apply_tool_loop_request_budget(
                prompt=prompt,
                system_prompt=system_prompt,
                tool_schemas=[],
                continuation_items=(),
                provider_continuation_state=None,
                continuation_support=continuation_support,
                run_budget=resolved_run_budget,
            )
            yield AssistantToolLoopIterationItem(
                raw_output=initial_raw_output
                or await model_caller(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    tools=[],
                )
            )
            return
        usage = _UsageTotals()
        output_items: list[dict[str, Any]] = []
        continuation_items: list[dict[str, Any]] = []
        normalized_input_items = list(getattr(turn_context, "normalized_input_items", []))
        provider_continuation_state: dict[str, Any] | None = None
        write_effective = False
        pending_output = initial_raw_output
        pending_output_already_streamed = False
        iteration = 0
        step_index = 0
        while True:
            iteration += 1
            if iteration > self.max_iterations:
                raise AssistantRuntimeTerminalError(
                    code="tool_loop_exhausted",
                    message="本轮工具调用次数已达上限，已停止继续执行。",
                )
            await _raise_if_cancelled(
                should_stop,
                write_effective=write_effective,
            )
            if pending_output is None:
                request_continuation_items, request_provider_state = apply_tool_loop_request_budget(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    tool_schemas=tool_schemas,
                    continuation_items=tuple(continuation_items),
                    provider_continuation_state=provider_continuation_state,
                    continuation_support=continuation_support,
                    run_budget=resolved_run_budget,
                )
                async for model_item in _iterate_model_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    tools=tool_schemas,
                    continuation_items=tuple(request_continuation_items),
                    provider_continuation_state=request_provider_state,
                    model_caller=model_caller,
                    stream_model_caller=stream_model_caller,
                ):
                    if model_item.raw_output is None:
                        yield model_item
                        continue
                    pending_output = model_item.raw_output
                    pending_output_already_streamed = model_item.raw_output_already_streamed
            raw_output = pending_output
            pending_output = None
            raw_output_already_streamed = pending_output_already_streamed
            pending_output_already_streamed = False
            _merge_usage_totals(usage, raw_output)
            tool_calls = _read_tool_calls(raw_output)
            if not tool_calls:
                final_normalized_items = _build_final_response_normalized_input_items(raw_output)
                if final_normalized_items:
                    normalized_input_items.extend(final_normalized_items)
                _record_tool_loop_state(
                    state_recorder,
                    pending_tool_calls_snapshot=(),
                    provider_continuation_state=provider_continuation_state,
                    normalized_input_items_snapshot=tuple(normalized_input_items),
                    write_effective=write_effective,
                )
                yield AssistantToolLoopIterationItem(
                    raw_output=_build_final_output(
                        turn_context=turn_context,
                        raw_output=raw_output,
                        usage=usage,
                        output_items=output_items,
                    ),
                    raw_output_already_streamed=raw_output_already_streamed,
                )
                return
            _ensure_serial_tool_calls(
                tool_calls,
                max_parallel_tool_calls=resolved_run_budget.max_parallel_tool_calls,
            )
            _record_tool_loop_state(
                state_recorder,
                pending_tool_calls_snapshot=_build_pending_tool_calls_snapshot(tool_calls),
                provider_continuation_state=provider_continuation_state,
                normalized_input_items_snapshot=tuple(normalized_input_items),
                write_effective=write_effective,
            )
            _append_intermediate_text_item(output_items, turn_context, raw_output)
            tool_results: list[AssistantToolResultEnvelope] = []
            planned_tool_calls, step_index = _plan_tool_cycle_calls(
                tool_calls=tool_calls,
                policy_decision_by_name=policy_decision_by_name,
                require_tool_descriptor=self._require_tool_descriptor,
                run_budget=resolved_run_budget,
                step_index=step_index,
            )
            for planned_tool_call in planned_tool_calls:
                await _raise_if_cancelled(should_stop)
                yield AssistantToolLoopIterationItem(
                    event_name="tool_call_start",
                    event_payload=_build_tool_call_start_payload(planned_tool_call.tool_call),
                )
                try:
                    tool_result = await self._execute_single_tool_call(
                        db,
                        step_index=planned_tool_call.step_index,
                        turn_context=turn_context,
                        owner_id=owner_id,
                        project_id=project_id,
                        tool_call=planned_tool_call.tool_call,
                        descriptor=planned_tool_call.descriptor,
                        tool_policy_decision=planned_tool_call.tool_policy_decision,
                        should_stop=should_stop,
                    )
                except StreamInterruptedError:
                    yield AssistantToolLoopIterationItem(
                        event_name="tool_call_result",
                        event_payload=_build_cancelled_tool_call_result_payload(
                            planned_tool_call.tool_call,
                        ),
                    )
                    raise
                except AssistantToolStatePersistError as exc:
                    yield AssistantToolLoopIterationItem(
                        event_name="tool_call_result",
                        event_payload=_build_state_persist_failed_tool_call_result_payload(
                            planned_tool_call.tool_call,
                            exc,
                        ),
                    )
                    raise
                except Exception as exc:
                    yield AssistantToolLoopIterationItem(
                        event_name="tool_call_result",
                        event_payload=_build_failed_tool_call_result_payload(
                            planned_tool_call.tool_call,
                            exc,
                        ),
                    )
                    raise
                tool_results.append(tool_result)
                write_effective = write_effective or _tool_result_committed_write(
                    descriptor=planned_tool_call.descriptor,
                    result=tool_result,
                )
                yield AssistantToolLoopIterationItem(
                    event_name="tool_call_result",
                    event_payload=_build_tool_call_result_payload(
                        planned_tool_call.tool_call,
                        tool_result,
                        descriptor=planned_tool_call.descriptor,
                    ),
                )
            cycle_output_items = _build_tool_cycle_output_items(
                turn_context=turn_context,
                start_index=len(output_items),
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
            output_items.extend(cycle_output_items)
            normalized_input_items.extend(
                _build_tool_cycle_normalized_input_items(
                    raw_output=raw_output,
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                )
            )
            cycle_continuation_items = _build_tool_cycle_continuation_items(
                raw_output=raw_output,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
            continuation_items.extend(cycle_continuation_items)
            provider_continuation_state = _resolve_provider_continuation_state(
                raw_output=raw_output,
                latest_items=cycle_continuation_items,
                continuation_support=continuation_support,
            )
            _record_tool_loop_state(
                state_recorder,
                pending_tool_calls_snapshot=(),
                provider_continuation_state=provider_continuation_state,
                normalized_input_items_snapshot=tuple(normalized_input_items),
                write_effective=write_effective,
            )

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
            await _raise_if_cancelled(should_stop)
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


def _serialize_tool_schema(descriptor: Any) -> dict[str, Any]:
    return {
        "name": descriptor.name,
        "description": descriptor.description,
        "parameters": descriptor.input_schema,
        "strict": True,
    }


def _read_tool_calls(raw_output: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls = raw_output.get("tool_calls")
    if tool_calls is None:
        return []
    if not isinstance(tool_calls, list):
        raise ConfigurationError("LLM tool_calls must be an array")
    normalized: list[dict[str, Any]] = []
    for item in tool_calls:
        if not isinstance(item, dict):
            raise ConfigurationError("LLM tool_calls entries must be objects")
        tool_call_id = item.get("tool_call_id")
        tool_name = item.get("tool_name")
        if not isinstance(tool_call_id, str) or not tool_call_id.strip():
            raise ConfigurationError("LLM tool_call_id must be a non-empty string")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ConfigurationError("LLM tool_name must be a non-empty string")
        normalized.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "arguments": item.get("arguments"),
                "arguments_text": item.get("arguments_text"),
                "provider_ref": item.get("provider_ref"),
            }
        )
    return normalized
async def _iterate_model_response(
    *,
    prompt: str,
    system_prompt: str | None,
    tools: list[dict[str, Any]],
    continuation_items: tuple[dict[str, Any], ...],
    provider_continuation_state: dict[str, Any] | None,
    model_caller: ToolModelCaller,
    stream_model_caller: ToolStreamModelCaller | None,
) -> AsyncIterator[AssistantToolLoopIterationItem]:
    if stream_model_caller is None:
        yield AssistantToolLoopIterationItem(
            raw_output=await model_caller(
                prompt=prompt,
                system_prompt=system_prompt,
                tools=tools,
                continuation_items=list(continuation_items),
                provider_continuation_state=provider_continuation_state,
            )
        )
        return
    streamed_output = False
    raw_output: dict[str, Any] | None = None
    async for event in stream_model_caller(
        prompt=prompt,
        system_prompt=system_prompt,
        tools=tools,
        continuation_items=list(continuation_items),
        provider_continuation_state=provider_continuation_state,
    ):
        if event.delta:
            streamed_output = True
            yield AssistantToolLoopIterationItem(
                event_name="chunk",
                event_payload={"delta": event.delta},
            )
        if event.raw_output is not None:
            raw_output = event.raw_output
    if raw_output is None:
        raise ConfigurationError("Streaming continuation completed without final output")
    yield AssistantToolLoopIterationItem(
        raw_output=raw_output,
        raw_output_already_streamed=streamed_output,
    )


def _ensure_serial_tool_calls(
    tool_calls: list[dict[str, Any]],
    *,
    max_parallel_tool_calls: int,
) -> None:
    if len(tool_calls) <= max_parallel_tool_calls:
        return
    raise AssistantRuntimeTerminalError(
        code="parallel_tool_calls_unsupported",
        message="当前运行时只支持串行工具调用，请逐个执行工具。",
    )


async def _raise_if_cancelled(
    should_stop: Callable[[], Awaitable[bool]] | None,
    *,
    write_effective: bool = False,
) -> None:
    if should_stop is None:
        return
    if await should_stop():
        if write_effective:
            raise build_cancel_requested_terminal_error(write_effective=True)
        raise StreamInterruptedError()


def _read_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _read_optional_record(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None
