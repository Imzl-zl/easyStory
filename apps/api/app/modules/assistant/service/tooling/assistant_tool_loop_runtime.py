from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError
from app.shared.runtime.llm.llm_protocol_types import LLMContinuationSupport
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse

from ..assistant_run_budget import AssistantRunBudget
from ..assistant_runtime_terminal import AssistantRuntimeTerminalError
from .assistant_tool_loop_context_support import (
    _build_continuation_request_snapshot,
    _build_pending_tool_calls_snapshot,
    _record_tool_loop_state,
)
from .assistant_tool_loop_budget_support import apply_tool_loop_request_budget
from .assistant_tool_loop_output_support import (
    _UsageTotals,
    _append_intermediate_text_item,
    _build_final_response_normalized_input_items,
    _build_final_output,
    _build_tool_cycle_continuation_items,
    _build_tool_cycle_normalized_input_items,
    _build_tool_cycle_output_items,
    _merge_usage_totals,
    _resolve_provider_continuation_state,
)
from .assistant_tool_loop_plan_support import _plan_tool_cycle_calls
from .assistant_tool_loop_result_support import (
    AssistantToolStatePersistError,
    _build_cancelled_tool_call_result_payload,
    _build_failed_tool_call_result_payload,
    _build_state_persist_failed_tool_call_result_payload,
    _build_tool_call_result_payload,
    _build_tool_call_start_payload,
    _tool_result_committed_write,
)
from .assistant_tool_loop_runtime_support import (
    ToolModelCaller,
    ToolStreamModelCaller,
    iterate_model_response,
    raise_if_cancelled,
    read_tool_calls,
)
from .assistant_tool_runtime_dto import (
    AssistantToolLoopStateRecorder,
    AssistantToolPolicyDecision,
    AssistantToolResultEnvelope,
)

if TYPE_CHECKING:
    from ..turn.assistant_turn_runtime_support import AssistantTurnContext
    from .assistant_tool_loop import AssistantToolLoop


@dataclass(frozen=True)
class AssistantToolLoopIterationItem:
    event_name: str | None = None
    event_payload: dict[str, Any] | None = None
    raw_output: LLMGenerateToolResponse | None = None
    raw_output_already_streamed: bool = False


@dataclass(frozen=True)
class AssistantToolLoopModelStreamEvent:
    delta: str | None = None
    raw_output: LLMGenerateToolResponse | None = None


class AssistantToolLoopGraphState(TypedDict, total=False):
    has_pending_output: bool
    has_tool_calls: bool
    iteration: int
    terminated: bool


class AssistantToolLoopRuntime:
    def __init__(
        self,
        *,
        tool_loop: "AssistantToolLoop",
        db: AsyncSession,
        turn_context: "AssistantTurnContext",
        owner_id: Any,
        project_id: Any,
        prompt: str,
        system_prompt: str | None,
        continuation_support: LLMContinuationSupport,
        model_caller: ToolModelCaller,
        stream_model_caller: ToolStreamModelCaller | None,
        initial_raw_output: LLMGenerateToolResponse | None,
        run_budget: AssistantRunBudget,
        tool_schemas: list[dict[str, Any]],
        policy_decision_by_name: dict[str, AssistantToolPolicyDecision],
        state_recorder: AssistantToolLoopStateRecorder | None,
        should_stop: Callable[[], Awaitable[bool]] | None,
    ) -> None:
        self.tool_loop = tool_loop
        self.db = db
        self.turn_context = turn_context
        self.owner_id = owner_id
        self.project_id = project_id
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.continuation_support = continuation_support
        self.model_caller = model_caller
        self.stream_model_caller = stream_model_caller
        self.pending_output = initial_raw_output
        self.run_budget = run_budget
        self.tool_schemas = tool_schemas
        self.policy_decision_by_name = policy_decision_by_name
        self.state_recorder = state_recorder
        self.should_stop = should_stop
        self.usage = _UsageTotals()
        self.output_items: list[dict[str, Any]] = []
        self.continuation_items: list[dict[str, Any]] = []
        self.normalized_input_items = list(getattr(turn_context, "normalized_input_items", []))
        self.provider_continuation_state: dict[str, Any] | None = None
        self.continuation_request_snapshot: dict[str, Any] | None = None
        self.continuation_compaction_snapshot: dict[str, Any] | None = None
        self.write_effective = False
        self.state_version = 1
        self.pending_output_already_streamed = False
        self.current_raw_output: LLMGenerateToolResponse | None = None
        self.current_raw_output_already_streamed = False
        self.current_tool_calls: list[dict[str, Any]] = []
        self.step_index = 0
        self.tool_cycle_index = 0
        self.final_iteration_item: AssistantToolLoopIterationItem | None = None
        self._graph = self._build_graph()

    async def iterate(self) -> AsyncIterator[AssistantToolLoopIterationItem]:
        if not self.tool_schemas:
            async for item in self._iterate_without_tools():
                yield item
            return
        initial_state: AssistantToolLoopGraphState = {
            "iteration": 0,
            "has_pending_output": self.pending_output is not None,
            "has_tool_calls": False,
            "terminated": False,
        }
        async for payload in self._graph.astream(initial_state, stream_mode="custom"):
            item = _deserialize_iteration_item(payload)
            if item is not None:
                yield item
        if self.final_iteration_item is None:
            raise ConfigurationError("Assistant tool loop graph completed without final output")
        yield self.final_iteration_item

    def _build_graph(self):
        graph = StateGraph(AssistantToolLoopGraphState)
        graph.add_node("advance_cycle", self._advance_cycle)
        graph.add_node("prepare_request", self._prepare_request)
        graph.add_node("call_model", self._call_model)
        graph.add_node("inspect_output", self._inspect_output)
        graph.add_node("execute_tool_cycle", self._execute_tool_cycle)
        graph.add_node("finalize_output", self._finalize_output)
        graph.add_edge(START, "advance_cycle")
        graph.add_conditional_edges(
            "advance_cycle",
            self._route_after_advance_cycle,
            {
                "prepare_request": "prepare_request",
                "inspect_output": "inspect_output",
            },
        )
        graph.add_edge("prepare_request", "call_model")
        graph.add_edge("call_model", "inspect_output")
        graph.add_conditional_edges(
            "inspect_output",
            self._route_after_inspect_output,
            {
                "execute_tool_cycle": "execute_tool_cycle",
                "finalize_output": "finalize_output",
            },
        )
        graph.add_edge("execute_tool_cycle", "advance_cycle")
        graph.add_edge("finalize_output", END)
        return graph.compile(name="assistant_tool_loop_runtime")

    async def _iterate_without_tools(self) -> AsyncIterator[AssistantToolLoopIterationItem]:
        await raise_if_cancelled(self.should_stop)
        apply_tool_loop_request_budget(
            prompt=self.prompt,
            system_prompt=self.system_prompt,
            tool_schemas=[],
            continuation_items=(),
            provider_continuation_state=None,
            continuation_support=self.continuation_support,
            run_budget=self.run_budget,
        )
        yield AssistantToolLoopIterationItem(
            raw_output=self.pending_output
            or await self.model_caller(
                prompt=self.prompt,
                system_prompt=self.system_prompt,
                tools=[],
            )
        )

    async def _advance_cycle(
        self,
        state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        iteration = state.get("iteration", 0) + 1
        if iteration > self.tool_loop.max_iterations:
            raise AssistantRuntimeTerminalError(
                code="tool_loop_exhausted",
                message="本轮工具调用次数已达上限，已停止继续执行。",
            )
        await raise_if_cancelled(
            self.should_stop,
            write_effective=self.write_effective,
        )
        return {
            "iteration": iteration,
            "has_pending_output": self.pending_output is not None,
            "terminated": False,
        }

    def _route_after_advance_cycle(self, state: AssistantToolLoopGraphState) -> str:
        if state.get("has_pending_output", False):
            return "inspect_output"
        return "prepare_request"

    async def _prepare_request(
        self,
        _state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        (
            request_continuation_items,
            request_provider_state,
            request_continuation_compaction_snapshot,
        ) = apply_tool_loop_request_budget(
            prompt=self.prompt,
            system_prompt=self.system_prompt,
            tool_schemas=self.tool_schemas,
            continuation_items=tuple(self.continuation_items),
            provider_continuation_state=self.provider_continuation_state,
            continuation_support=self.continuation_support,
            run_budget=self.run_budget,
        )
        self.continuation_request_snapshot = _build_continuation_request_snapshot(
            continuation_items=tuple(request_continuation_items),
            provider_continuation_state=request_provider_state,
        )
        if request_continuation_compaction_snapshot is not None:
            self.continuation_compaction_snapshot = request_continuation_compaction_snapshot
        self._record_state(pending_tool_calls_snapshot=())
        self._request_continuation_items = tuple(request_continuation_items)
        self._request_provider_state = request_provider_state
        return {"has_pending_output": False}

    async def _call_model(
        self,
        _state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        async for model_item in iterate_model_response(
            prompt=self.prompt,
            system_prompt=self.system_prompt,
            tools=self.tool_schemas,
            continuation_items=self._request_continuation_items,
            provider_continuation_state=self._request_provider_state,
            model_caller=self.model_caller,
            stream_model_caller=self.stream_model_caller,
        ):
            if model_item.raw_output is None:
                self._emit_iteration_item(model_item)
                continue
            self.pending_output = model_item.raw_output
            self.pending_output_already_streamed = model_item.raw_output_already_streamed
        return {"has_pending_output": self.pending_output is not None}

    async def _inspect_output(
        self,
        _state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        raw_output = self.pending_output
        if raw_output is None:
            raise ConfigurationError("Assistant tool loop runtime missing pending raw output")
        self.pending_output = None
        self.current_raw_output = raw_output
        self.current_raw_output_already_streamed = self.pending_output_already_streamed
        self.pending_output_already_streamed = False
        _merge_usage_totals(self.usage, raw_output)
        self.current_tool_calls = read_tool_calls(raw_output)
        return {
            "has_tool_calls": bool(self.current_tool_calls),
            "has_pending_output": False,
            "terminated": not bool(self.current_tool_calls),
        }

    def _route_after_inspect_output(self, state: AssistantToolLoopGraphState) -> str:
        if state.get("has_tool_calls", False):
            return "execute_tool_cycle"
        return "finalize_output"

    async def _execute_tool_cycle(
        self,
        _state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        raw_output = self._require_current_raw_output()
        tool_calls = list(self.current_tool_calls)
        self._record_state(
            pending_tool_calls_snapshot=_build_pending_tool_calls_snapshot(tool_calls)
        )
        _append_intermediate_text_item(self.output_items, self.turn_context, raw_output)
        tool_results: list[AssistantToolResultEnvelope] = []
        planned_tool_calls, self.step_index = _plan_tool_cycle_calls(
            tool_calls=tool_calls,
            policy_decision_by_name=self.policy_decision_by_name,
            require_tool_descriptor=self.tool_loop._require_tool_descriptor,
            run_budget=self.run_budget,
            step_index=self.step_index,
        )
        for planned_tool_call in planned_tool_calls:
            await raise_if_cancelled(self.should_stop)
            self._emit_iteration_item(
                AssistantToolLoopIterationItem(
                    event_name="tool_call_start",
                    event_payload=_build_tool_call_start_payload(planned_tool_call.tool_call),
                )
            )
            try:
                tool_result = await self.tool_loop._execute_single_tool_call(
                    self.db,
                    step_index=planned_tool_call.step_index,
                    turn_context=self.turn_context,
                    owner_id=self.owner_id,
                    project_id=self.project_id,
                    tool_call=planned_tool_call.tool_call,
                    descriptor=planned_tool_call.descriptor,
                    tool_policy_decision=planned_tool_call.tool_policy_decision,
                    should_stop=self.should_stop,
                )
            except StreamInterruptedError:
                self._emit_iteration_item(
                    AssistantToolLoopIterationItem(
                        event_name="tool_call_result",
                        event_payload=_build_cancelled_tool_call_result_payload(
                            planned_tool_call.tool_call,
                        ),
                    )
                )
                raise
            except AssistantToolStatePersistError as exc:
                self._emit_iteration_item(
                    AssistantToolLoopIterationItem(
                        event_name="tool_call_result",
                        event_payload=_build_state_persist_failed_tool_call_result_payload(
                            planned_tool_call.tool_call,
                            exc,
                        ),
                    )
                )
                raise
            except Exception as exc:
                self._emit_iteration_item(
                    AssistantToolLoopIterationItem(
                        event_name="tool_call_result",
                        event_payload=_build_failed_tool_call_result_payload(
                            planned_tool_call.tool_call,
                            exc,
                        ),
                    )
                )
                raise
            tool_results.append(tool_result)
            self.write_effective = self.write_effective or _tool_result_committed_write(
                descriptor=planned_tool_call.descriptor,
                result=tool_result,
            )
            self._emit_iteration_item(
                AssistantToolLoopIterationItem(
                    event_name="tool_call_result",
                    event_payload=_build_tool_call_result_payload(
                        planned_tool_call.tool_call,
                        tool_result,
                        descriptor=planned_tool_call.descriptor,
                    ),
                )
            )
        cycle_output_items = _build_tool_cycle_output_items(
            turn_context=self.turn_context,
            start_index=len(self.output_items),
            tool_calls=tool_calls,
            tool_results=tool_results,
        )
        self.output_items.extend(cycle_output_items)
        self.normalized_input_items.extend(
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
            tool_cycle_index=self.tool_cycle_index,
        )
        self.continuation_items.extend(cycle_continuation_items)
        self.provider_continuation_state = _resolve_provider_continuation_state(
            raw_output=raw_output,
            latest_items=cycle_continuation_items,
            continuation_support=self.continuation_support,
        )
        self._record_state(pending_tool_calls_snapshot=())
        self.tool_cycle_index += 1
        self.current_tool_calls = []
        self.current_raw_output = None
        self.current_raw_output_already_streamed = False
        return {
            "has_tool_calls": False,
            "has_pending_output": False,
            "terminated": False,
        }

    async def _finalize_output(
        self,
        _state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        raw_output = self._require_current_raw_output()
        final_normalized_items = _build_final_response_normalized_input_items(raw_output)
        if final_normalized_items:
            self.normalized_input_items.extend(final_normalized_items)
        self._record_state(pending_tool_calls_snapshot=())
        self.final_iteration_item = AssistantToolLoopIterationItem(
            raw_output=_build_final_output(
                turn_context=self.turn_context,
                raw_output=raw_output,
                usage=self.usage,
                output_items=self.output_items,
            ),
            raw_output_already_streamed=self.current_raw_output_already_streamed,
        )
        self.current_raw_output = None
        self.current_raw_output_already_streamed = False
        return {"terminated": True}

    def _record_state(
        self,
        *,
        pending_tool_calls_snapshot: tuple[dict[str, Any], ...],
    ) -> None:
        self.state_version += 1
        _record_tool_loop_state(
            self.state_recorder,
            pending_tool_calls_snapshot=pending_tool_calls_snapshot,
            provider_continuation_state=self.provider_continuation_state,
            normalized_input_items_snapshot=tuple(self.normalized_input_items),
            continuation_request_snapshot=self.continuation_request_snapshot,
            continuation_compaction_snapshot=self.continuation_compaction_snapshot,
            write_effective=self.write_effective,
        )

    def _emit_iteration_item(self, item: AssistantToolLoopIterationItem) -> None:
        writer = get_stream_writer()
        writer(
            _serialize_iteration_item(
                item,
                state_version=(
                    self.state_version if self.state_recorder is not None else None
                ),
            )
        )

    def _require_current_raw_output(self) -> LLMGenerateToolResponse:
        if self.current_raw_output is None:
            raise ConfigurationError("Assistant tool loop runtime missing current raw output")
        return self.current_raw_output

def _serialize_iteration_item(
    item: AssistantToolLoopIterationItem,
    *,
    state_version: int | None,
) -> dict[str, Any]:
    event_payload = item.event_payload
    if event_payload is not None and state_version is not None:
        event_payload = {**event_payload, "state_version": state_version}
    return {
        "kind": "assistant_tool_loop_iteration_item",
        "event_name": item.event_name,
        "event_payload": event_payload,
        "raw_output": item.raw_output,
        "raw_output_already_streamed": item.raw_output_already_streamed,
    }


def _deserialize_iteration_item(payload: Any) -> AssistantToolLoopIterationItem | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != "assistant_tool_loop_iteration_item":
        return None
    return AssistantToolLoopIterationItem(
        event_name=payload.get("event_name"),
        event_payload=payload.get("event_payload"),
        raw_output=payload.get("raw_output"),
        raw_output_already_streamed=bool(payload.get("raw_output_already_streamed")),
    )
