from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol_types import LLMContinuationSupport
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse

from ..assistant_run_budget import AssistantRunBudget
from ..assistant_runtime_terminal import AssistantRuntimeTerminalError
from .assistant_tool_loop_context_support import _build_continuation_request_snapshot, _build_pending_tool_calls_snapshot
from .assistant_tool_loop_execution_support import build_post_tool_cycle_state, execute_planned_tool_calls
from .assistant_tool_loop_graph_state_support import (
    INITIAL_TOOL_LOOP_STATE_VERSION,
    AssistantToolLoopGraphState,
    build_initial_graph_state,
    deserialize_iteration_item,
    record_graph_state,
    require_current_raw_output,
    resolve_tool_loop_recursion_limit,
    serialize_iteration_item,
)
from .assistant_tool_loop_budget_support import apply_tool_loop_request_budget
from .assistant_tool_loop_output_support import (
    _append_intermediate_text_item,
    _build_final_output,
    _build_final_response_normalized_input_items,
    _merge_usage_totals_state,
)
from .assistant_tool_loop_plan_support import _plan_tool_cycle_calls
from .assistant_tool_loop_runtime_support import ToolModelCaller, ToolStreamModelCaller, iterate_model_response, raise_if_cancelled, read_tool_calls
from .assistant_tool_runtime_dto import AssistantToolLoopStateRecorder, AssistantToolPolicyDecision

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
        self.initial_raw_output = initial_raw_output
        self.run_budget = run_budget
        self.tool_schemas = tool_schemas
        self.policy_decision_by_name = policy_decision_by_name
        self.state_recorder = state_recorder
        self.should_stop = should_stop
        self._graph = self._build_graph()

    async def iterate(self) -> AsyncIterator[AssistantToolLoopIterationItem]:
        # This runtime relies on LangGraph's custom stream context.
        # Calling it via ainvoke()/invoke() would make get_stream_writer() unavailable.
        if not self.tool_schemas:
            async for item in self._iterate_without_tools():
                yield item
            return
        saw_final_output = False
        async for payload in self._graph.astream(
            build_initial_graph_state(
                self.turn_context,
                initial_raw_output=self.initial_raw_output,
            ),
            stream_mode="custom",
            config={
                "recursion_limit": resolve_tool_loop_recursion_limit(
                    self.tool_loop.max_iterations
                )
            },
        ):
            item = deserialize_iteration_item(
                payload,
                build_iteration_item=AssistantToolLoopIterationItem,
            )
            if item is None:
                continue
            if item.raw_output is not None:
                saw_final_output = True
            yield item
        if not saw_final_output:
            raise ConfigurationError("Assistant tool loop graph completed without final output")

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
            raw_output=self.initial_raw_output
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
            write_effective=state.get("write_effective", False),
        )
        return {"iteration": iteration}

    def _route_after_advance_cycle(self, state: AssistantToolLoopGraphState) -> str:
        if state.get("pending_output") is not None:
            return "inspect_output"
        return "prepare_request"

    async def _prepare_request(
        self,
        state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        (
            request_continuation_items,
            request_provider_state,
            request_continuation_compaction_snapshot,
        ) = apply_tool_loop_request_budget(
            prompt=self.prompt,
            system_prompt=self.system_prompt,
            tool_schemas=self.tool_schemas,
            continuation_items=tuple(state.get("continuation_items", [])),
            provider_continuation_state=state.get("provider_continuation_state"),
            continuation_support=self.continuation_support,
            run_budget=self.run_budget,
        )
        continuation_request_snapshot = _build_continuation_request_snapshot(
            continuation_items=tuple(request_continuation_items),
            provider_continuation_state=request_provider_state,
        )
        continuation_compaction_snapshot = (
            request_continuation_compaction_snapshot
            if request_continuation_compaction_snapshot is not None
            else state.get("continuation_compaction_snapshot")
        )
        state_version = record_graph_state(
            self.state_recorder,
            current_state_version=state.get("state_version", INITIAL_TOOL_LOOP_STATE_VERSION),
            provider_continuation_state=state.get("provider_continuation_state"),
            normalized_input_items=state.get("normalized_input_items", []),
            continuation_request_snapshot=continuation_request_snapshot,
            continuation_compaction_snapshot=continuation_compaction_snapshot,
            write_effective=state.get("write_effective", False),
            pending_tool_calls_snapshot=(),
        )
        return {
            "request_continuation_items": list(request_continuation_items),
            "request_provider_state": request_provider_state,
            "continuation_request_snapshot": continuation_request_snapshot,
            "continuation_compaction_snapshot": continuation_compaction_snapshot,
            "state_version": state_version,
        }

    async def _call_model(
        self,
        state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        pending_output = state.get("pending_output")
        pending_output_already_streamed = state.get("pending_output_already_streamed", False)
        state_version = state.get("state_version", INITIAL_TOOL_LOOP_STATE_VERSION)
        async for model_item in iterate_model_response(
            prompt=self.prompt,
            system_prompt=self.system_prompt,
            tools=self.tool_schemas,
            continuation_items=tuple(state.get("request_continuation_items", [])),
            provider_continuation_state=state.get("request_provider_state"),
            model_caller=self.model_caller,
            stream_model_caller=self.stream_model_caller,
        ):
            if model_item.raw_output is None:
                self._emit_iteration_item(
                    model_item,
                    state_version=state_version,
                )
                continue
            pending_output = model_item.raw_output
            pending_output_already_streamed = model_item.raw_output_already_streamed
        return {
            "pending_output": pending_output,
            "pending_output_already_streamed": pending_output_already_streamed,
        }

    async def _inspect_output(
        self,
        state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        raw_output = state.get("pending_output")
        if raw_output is None:
            raise ConfigurationError("Assistant tool loop runtime missing pending raw output")
        return {
            "pending_output": None,
            "pending_output_already_streamed": False,
            "current_raw_output": raw_output,
            "current_raw_output_already_streamed": state.get(
                "pending_output_already_streamed",
                False,
            ),
            "usage": _merge_usage_totals_state(
                state["usage"],
                raw_output,
            ),
            "current_tool_calls": read_tool_calls(raw_output),
        }

    def _route_after_inspect_output(self, state: AssistantToolLoopGraphState) -> str:
        if state.get("current_tool_calls"):
            return "execute_tool_cycle"
        return "finalize_output"

    async def _execute_tool_cycle(
        self,
        state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        raw_output = require_current_raw_output(state)
        tool_calls = list(state.get("current_tool_calls", []))
        pre_execution_state_version = record_graph_state(
            self.state_recorder,
            current_state_version=state.get("state_version", INITIAL_TOOL_LOOP_STATE_VERSION),
            provider_continuation_state=state.get("provider_continuation_state"),
            normalized_input_items=state.get("normalized_input_items", []),
            continuation_request_snapshot=state.get("continuation_request_snapshot"),
            continuation_compaction_snapshot=state.get("continuation_compaction_snapshot"),
            write_effective=state.get("write_effective", False),
            pending_tool_calls_snapshot=_build_pending_tool_calls_snapshot(tool_calls),
        )
        output_items = list(state.get("output_items", []))
        _append_intermediate_text_item(output_items, self.turn_context, raw_output)
        planned_tool_calls, step_index = _plan_tool_cycle_calls(
            tool_calls=tool_calls,
            policy_decision_by_name=self.policy_decision_by_name,
            require_tool_descriptor=self.tool_loop._require_tool_descriptor,
            run_budget=self.run_budget,
            step_index=state.get("step_index", 0),
        )
        tool_results, write_effective = await execute_planned_tool_calls(
            planned_tool_calls=planned_tool_calls,
            state_version=pre_execution_state_version,
            initial_write_effective=state.get("write_effective", False),
            should_stop=self.should_stop,
            execute_single_tool_call=lambda planned_tool_call: self.tool_loop._execute_single_tool_call(
                self.db,
                step_index=planned_tool_call.step_index,
                turn_context=self.turn_context,
                owner_id=self.owner_id,
                project_id=self.project_id,
                tool_call=planned_tool_call.tool_call,
                descriptor=planned_tool_call.descriptor,
                tool_policy_decision=planned_tool_call.tool_policy_decision,
                should_stop=self.should_stop,
            ),
            emit_iteration_item=self._emit_iteration_item,
            build_iteration_item=AssistantToolLoopIterationItem,
        )
        post_cycle_state = build_post_tool_cycle_state(
            state=state,
            raw_output=raw_output,
            tool_calls=tool_calls,
            tool_results=tool_results,
            turn_context=self.turn_context,
            continuation_support=self.continuation_support,
            output_items=output_items,
            write_effective=write_effective,
            step_index=step_index,
        )
        post_execution_state_version = record_graph_state(
            self.state_recorder,
            current_state_version=pre_execution_state_version,
            provider_continuation_state=post_cycle_state["provider_continuation_state"],
            normalized_input_items=post_cycle_state["normalized_input_items"],
            continuation_request_snapshot=state.get("continuation_request_snapshot"),
            continuation_compaction_snapshot=state.get("continuation_compaction_snapshot"),
            write_effective=write_effective,
            pending_tool_calls_snapshot=(),
        )
        return {
            "state_version": post_execution_state_version,
            **post_cycle_state,
        }

    async def _finalize_output(
        self,
        state: AssistantToolLoopGraphState,
    ) -> AssistantToolLoopGraphState:
        raw_output = require_current_raw_output(state)
        normalized_input_items = list(state.get("normalized_input_items", []))
        final_normalized_items = _build_final_response_normalized_input_items(raw_output)
        if final_normalized_items:
            normalized_input_items.extend(final_normalized_items)
        state_version = record_graph_state(
            self.state_recorder,
            current_state_version=state.get("state_version", INITIAL_TOOL_LOOP_STATE_VERSION),
            provider_continuation_state=state.get("provider_continuation_state"),
            normalized_input_items=normalized_input_items,
            continuation_request_snapshot=state.get("continuation_request_snapshot"),
            continuation_compaction_snapshot=state.get("continuation_compaction_snapshot"),
            write_effective=state.get("write_effective", False),
            pending_tool_calls_snapshot=(),
        )
        self._emit_iteration_item(
            AssistantToolLoopIterationItem(
                raw_output=_build_final_output(
                    turn_context=self.turn_context,
                    raw_output=raw_output,
                    usage=state["usage"],
                    output_items=state.get("output_items", []),
                ),
                raw_output_already_streamed=state.get("current_raw_output_already_streamed", False),
            ),
            state_version=state_version,
        )
        return {
            "state_version": state_version,
            "normalized_input_items": normalized_input_items,
            "current_raw_output": None,
            "current_raw_output_already_streamed": False,
            "current_tool_calls": [],
        }

    def _emit_iteration_item(
        self,
        item: AssistantToolLoopIterationItem,
        *,
        state_version: int,
    ) -> None:
        writer = get_stream_writer()
        if writer is None:
            raise ConfigurationError(
                "Assistant tool loop runtime requires astream(stream_mode='custom') to emit iteration events"
            )
        writer(
            serialize_iteration_item(
                item,
                state_version=state_version if self.state_recorder is not None else None,
            )
        )
