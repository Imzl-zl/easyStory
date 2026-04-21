from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse, LLMStreamEvent


class AssistantTurnResponsePayload(Protocol):
    def model_dump(self, *, mode: str) -> dict[str, Any]: ...


class AssistantTurnStreamExecutionGraphState(TypedDict, total=False):
    before_results: list[Any]
    raw_output: LLMGenerateToolResponse
    response: AssistantTurnResponsePayload


class AssistantTurnStreamExecutionRuntime:
    def __init__(
        self,
        *,
        replayed_response: AssistantTurnResponsePayload | None,
        build_stream_event_data: Callable[[int, dict[str, Any] | None], dict[str, Any]],
        run_started_extra: dict[str, Any],
        run_before_hooks: Callable[[], Awaitable[list[Any]]],
        should_stream_with_tool_loop: bool,
        stream_tool_loop: Callable[[], AsyncIterator[tuple[str, dict[str, Any]]]],
        call_turn_llm_stream: Callable[[], AsyncIterator[LLMStreamEvent]],
        finalize_response: Callable[[list[Any], LLMGenerateToolResponse], Awaitable[AssistantTurnResponsePayload]],
        run_prepared_on_error_hooks: Callable[[Exception], Awaitable[Exception | None]],
        store_terminal_turn: Callable[..., Awaitable[None]],
        attach_stream_error_meta: Callable[[Exception, dict[str, Any]], None],
    ) -> None:
        self.replayed_response = replayed_response
        self.build_stream_event_data = build_stream_event_data
        self.run_started_extra = dict(run_started_extra)
        self.run_before_hooks = run_before_hooks
        self.should_stream_with_tool_loop = should_stream_with_tool_loop
        self.stream_tool_loop = stream_tool_loop
        self.call_turn_llm_stream = call_turn_llm_stream
        self.finalize_response = finalize_response
        self.run_prepared_on_error_hooks = run_prepared_on_error_hooks
        self.store_terminal_turn = store_terminal_turn
        self.attach_stream_error_meta = attach_stream_error_meta
        self.event_seq = 0
        self._graph = self._build_graph()

    async def iterate(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        # This runtime must be consumed via LangGraph astream(stream_mode="custom"),
        # otherwise get_stream_writer() is unavailable for event emission.
        try:
            async for payload in self._graph.astream({}, stream_mode="custom"):
                event = _deserialize_stream_event(payload)
                if event is None:
                    continue
                yield event
        except Exception as exc:
            hook_error = await self.run_prepared_on_error_hooks(exc)
            await self.store_terminal_turn(error=hook_error or exc)
            stream_error = hook_error or exc
            self.attach_stream_error_meta(
                stream_error,
                self.build_stream_event_data(self.event_seq + 1, None),
            )
            if hook_error is not None:
                raise hook_error
            raise

    def _build_graph(self):
        graph = StateGraph(AssistantTurnStreamExecutionGraphState)
        graph.add_node("emit_run_started", self._emit_run_started)
        graph.add_node("emit_replayed_completed", self._emit_replayed_completed)
        graph.add_node("run_before_hooks", self._run_before_hooks)
        graph.add_node("stream_response", self._stream_response)
        graph.add_node("finalize_response", self._finalize_response)
        graph.add_node("emit_completed", self._emit_completed)
        graph.add_edge(START, "emit_run_started")
        graph.add_conditional_edges(
            "emit_run_started",
            self._route_after_run_started,
            {
                "emit_replayed_completed": "emit_replayed_completed",
                "run_before_hooks": "run_before_hooks",
            },
        )
        graph.add_edge("emit_replayed_completed", END)
        graph.add_edge("run_before_hooks", "stream_response")
        graph.add_edge("stream_response", "finalize_response")
        graph.add_edge("finalize_response", "emit_completed")
        graph.add_edge("emit_completed", END)
        return graph.compile(name="assistant_turn_stream_execution_runtime")

    async def _emit_run_started(
        self,
        _state: AssistantTurnStreamExecutionGraphState,
    ) -> AssistantTurnStreamExecutionGraphState:
        self._emit_event(
            "run_started",
            self.run_started_extra,
        )
        return {}

    def _route_after_run_started(
        self,
        _state: AssistantTurnStreamExecutionGraphState,
    ) -> str:
        if self.replayed_response is not None:
            return "emit_replayed_completed"
        return "run_before_hooks"

    async def _emit_replayed_completed(
        self,
        _state: AssistantTurnStreamExecutionGraphState,
    ) -> AssistantTurnStreamExecutionGraphState:
        replayed_response = self._require_response(self.replayed_response)
        self._emit_completed_event(replayed_response)
        return {"response": replayed_response}

    async def _run_before_hooks(
        self,
        _state: AssistantTurnStreamExecutionGraphState,
    ) -> AssistantTurnStreamExecutionGraphState:
        return {"before_results": await self.run_before_hooks()}

    async def _stream_response(
        self,
        _state: AssistantTurnStreamExecutionGraphState,
    ) -> AssistantTurnStreamExecutionGraphState:
        raw_output: LLMGenerateToolResponse | None = None
        if self.should_stream_with_tool_loop:
            async for event_name, event_data in self.stream_tool_loop():
                if event_name == "final_output":
                    raw_output = event_data
                    continue
                self._emit_event(event_name, event_data)
        else:
            async for event in self.call_turn_llm_stream():
                if event.delta:
                    self._emit_event("chunk", {"delta": event.delta})
                    continue
                raw_output = event.response
        if raw_output is None:
            raise ConfigurationError("Streaming response completed without final output")
        return {"raw_output": raw_output}

    async def _finalize_response(
        self,
        state: AssistantTurnStreamExecutionGraphState,
    ) -> AssistantTurnStreamExecutionGraphState:
        before_results = state.get("before_results")
        raw_output = state.get("raw_output")
        if before_results is None or raw_output is None:
            raise ConfigurationError("Assistant stream execution runtime missing intermediate state")
        return {
            "response": await self.finalize_response(before_results, raw_output),
        }

    async def _emit_completed(
        self,
        state: AssistantTurnStreamExecutionGraphState,
    ) -> AssistantTurnStreamExecutionGraphState:
        response = self._require_response(state.get("response"))
        await self.store_terminal_turn(response=response)
        self._emit_completed_event(response)
        return {"response": response}

    def _emit_event(self, event_name: str, extra: dict[str, Any] | None) -> None:
        self.event_seq += 1
        writer = get_stream_writer()
        if writer is None:
            raise ConfigurationError(
                "Assistant turn stream runtime requires astream(stream_mode='custom') to emit events"
            )
        writer(
            {
                "kind": "assistant_turn_stream_execution_event",
                "event_name": event_name,
                "event_data": self.build_stream_event_data(self.event_seq, extra),
            }
        )

    def _emit_completed_event(self, response: AssistantTurnResponsePayload) -> None:
        self.event_seq += 1
        payload = response.model_dump(mode="json")
        payload.update(self.build_stream_event_data(self.event_seq, None))
        writer = get_stream_writer()
        if writer is None:
            raise ConfigurationError(
                "Assistant turn stream runtime requires astream(stream_mode='custom') to emit events"
            )
        writer(
            {
                "kind": "assistant_turn_stream_execution_event",
                "event_name": "completed",
                "event_data": payload,
            }
        )

    @staticmethod
    def _require_response(
        response: AssistantTurnResponsePayload | None,
    ) -> AssistantTurnResponsePayload:
        if response is None:
            raise ConfigurationError("Assistant stream execution runtime completed without response")
        return response


def _deserialize_stream_event(payload: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != "assistant_turn_stream_execution_event":
        return None
    event_name = payload.get("event_name")
    event_data = payload.get("event_data")
    if not isinstance(event_name, str) or not isinstance(event_data, dict):
        return None
    return event_name, event_data
