from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol, TypedDict
import uuid

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse, LLMStreamEvent

from ..assistant_llm_runtime_support import (
    build_tool_loop_model_caller,
    build_tool_loop_stream_model_caller,
)
from ..tooling.assistant_tool_loop import AssistantToolLoop
from .assistant_turn_llm_bridge_support import build_turn_tool_loop_state_recorder
from .assistant_turn_run_store import AssistantTurnRunStore
from .assistant_turn_runtime_support import PreparedAssistantTurn


class AssistantTurnResolveLlmRuntime(Protocol):
    async def __call__(
        self,
        db: AsyncSession,
        *,
        model: Any,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
    ) -> Any: ...


class AssistantTurnCallLlm(Protocol):
    async def __call__(
        self,
        db: AsyncSession,
        *,
        prompt: str,
        system_prompt: str | None,
        model: Any,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        runtime_context: Any | None = None,
        continuation_items: list[dict[str, Any]] | None = None,
        provider_continuation_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class AssistantTurnCallLlmStream(Protocol):
    def __call__(
        self,
        db: AsyncSession,
        *,
        prompt: str,
        system_prompt: str | None,
        model: Any,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        runtime_context: Any | None = None,
        tools: list[dict[str, Any]] | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
        continuation_items: list[dict[str, Any]] | None = None,
        provider_continuation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]: ...


class AssistantTurnToolStreamGraphState(TypedDict, total=False):
    has_tool_calls: bool
    has_final_output: bool


class AssistantTurnToolStreamRuntime:
    def __init__(
        self,
        *,
        db: AsyncSession,
        prepared: PreparedAssistantTurn,
        owner_id: uuid.UUID,
        should_stop: Callable[[], Awaitable[bool]] | None,
        assistant_tool_loop: AssistantToolLoop,
        turn_run_store: AssistantTurnRunStore | None,
        resolve_llm_runtime: AssistantTurnResolveLlmRuntime,
        call_llm: AssistantTurnCallLlm,
        call_llm_stream: AssistantTurnCallLlmStream,
        runtime_context: Any | None = None,
    ) -> None:
        self.db = db
        self.prepared = prepared
        self.owner_id = owner_id
        self.should_stop = should_stop
        self.assistant_tool_loop = assistant_tool_loop
        self.turn_run_store = turn_run_store
        self.resolve_llm_runtime = resolve_llm_runtime
        self.call_llm = call_llm
        self.call_llm_stream = call_llm_stream
        self.runtime_context = runtime_context
        self.tool_schemas = self.assistant_tool_loop.resolve_tool_schemas(
            turn_context=self.prepared.turn_context,
            project_id=self.prepared.project_id,
            visible_descriptors=self.prepared.visible_tool_descriptors,
        )
        if not self.tool_schemas:
            raise ConfigurationError("Assistant tool loop streaming requires visible tools")
        self.current_raw_output: LLMGenerateToolResponse | None = None
        self.final_output: LLMGenerateToolResponse | None = None
        self._graph = self._build_graph()

    async def iterate(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        # This runtime must be consumed via LangGraph astream(stream_mode="custom"),
        # otherwise get_stream_writer() is unavailable for event emission.
        async for payload in self._graph.astream({}, stream_mode="custom"):
            event = _deserialize_stream_event(payload)
            if event is None:
                continue
            yield event
        if self.final_output is None:
            raise ConfigurationError("Assistant turn tool stream completed without final output")
        yield "final_output", self.final_output

    def _build_graph(self):
        graph = StateGraph(AssistantTurnToolStreamGraphState)
        graph.add_node("stream_initial_response", self._stream_initial_response)
        graph.add_node("finalize_initial_output", self._finalize_initial_output)
        graph.add_node("stream_followup", self._stream_followup)
        graph.add_edge(START, "stream_initial_response")
        graph.add_conditional_edges(
            "stream_initial_response",
            self._route_after_initial_response,
            {
                "finalize_initial_output": "finalize_initial_output",
                "stream_followup": "stream_followup",
            },
        )
        graph.add_edge("finalize_initial_output", END)
        graph.add_edge("stream_followup", END)
        return graph.compile(name="assistant_turn_tool_stream_runtime")

    async def _stream_initial_response(
        self,
        _state: AssistantTurnToolStreamGraphState,
    ) -> AssistantTurnToolStreamGraphState:
        resolved_runtime = await self._resolve_runtime_context()
        async for event in self.call_llm_stream(
            self.db,
            prompt=self.prepared.prompt,
            system_prompt=self.prepared.system_prompt,
            model=self.prepared.spec.model,
            owner_id=self.owner_id,
            project_id=self.prepared.project_id,
            runtime_context=resolved_runtime,
            tools=self.tool_schemas,
            should_stop=self.should_stop,
        ):
            if event.delta:
                _emit_stream_event("chunk", {"delta": event.delta})
                continue
            self.current_raw_output = event.response
        raw_output = self._require_current_raw_output()
        return {
            "has_tool_calls": _has_tool_calls(raw_output),
            "has_final_output": False,
        }

    def _route_after_initial_response(
        self,
        state: AssistantTurnToolStreamGraphState,
    ) -> str:
        if state.get("has_tool_calls", False):
            return "stream_followup"
        return "finalize_initial_output"

    async def _finalize_initial_output(
        self,
        _state: AssistantTurnToolStreamGraphState,
    ) -> AssistantTurnToolStreamGraphState:
        self.final_output = self._require_current_raw_output()
        self.current_raw_output = None
        return {"has_final_output": True}

    async def _stream_followup(
        self,
        _state: AssistantTurnToolStreamGraphState,
    ) -> AssistantTurnToolStreamGraphState:
        resolved_runtime = await self._resolve_runtime_context()
        async for item in self.assistant_tool_loop.iterate(
            self.db,
            turn_context=self.prepared.turn_context,
            owner_id=self.owner_id,
            project_id=self.prepared.project_id,
            prompt=self.prepared.prompt,
            system_prompt=self.prepared.system_prompt,
            continuation_support=resolved_runtime.continuation_support,
            model_caller=build_tool_loop_model_caller(
                llm_caller=self.call_llm,
                db=self.db,
                model=self.prepared.spec.model,
                owner_id=self.owner_id,
                project_id=self.prepared.project_id,
                runtime_context=resolved_runtime,
            ),
            stream_model_caller=build_tool_loop_stream_model_caller(
                llm_stream_caller=self.call_llm_stream,
                db=self.db,
                model=self.prepared.spec.model,
                owner_id=self.owner_id,
                project_id=self.prepared.project_id,
                runtime_context=resolved_runtime,
                should_stop=self.should_stop,
            ),
            initial_raw_output=self._require_current_raw_output(),
            run_budget=self.prepared.run_budget,
            tool_policy_decisions=self.prepared.tool_policy_decisions,
            visible_descriptors=self.prepared.visible_tool_descriptors,
            state_recorder=build_turn_tool_loop_state_recorder(
                turn_run_store=self.turn_run_store,
                run_id=self.prepared.turn_context.run_id,
            ),
            should_stop=self.should_stop,
        ):
            if item.event_name is not None and item.event_payload is not None:
                _emit_stream_event(item.event_name, item.event_payload)
                continue
            if item.raw_output is None:
                continue
            buffered_chunk = (
                None
                if item.raw_output_already_streamed
                else _build_buffered_final_chunk_payload(item.raw_output)
            )
            if buffered_chunk is not None:
                _emit_stream_event("chunk", buffered_chunk)
            self.final_output = item.raw_output
        if self.final_output is None:
            raise ConfigurationError("Assistant tool loop follow-up completed without final output")
        self.current_raw_output = None
        return {"has_final_output": True}

    async def _resolve_runtime_context(self) -> Any:
        if self.runtime_context is not None:
            return self.runtime_context
        self.runtime_context = await self.resolve_llm_runtime(
            self.db,
            model=self.prepared.spec.model,
            owner_id=self.owner_id,
            project_id=self.prepared.project_id,
        )
        return self.runtime_context

    def _require_current_raw_output(self) -> LLMGenerateToolResponse:
        if self.current_raw_output is None:
            raise ConfigurationError("Streaming response completed without initial output")
        return self.current_raw_output


def _has_tool_calls(raw_output: LLMGenerateToolResponse) -> bool:
    tool_calls = raw_output.get("tool_calls")
    return isinstance(tool_calls, list) and bool(tool_calls)


def _build_buffered_final_chunk_payload(
    raw_output: LLMGenerateToolResponse,
) -> dict[str, Any] | None:
    content = raw_output.get("content")
    if not isinstance(content, str) or not content:
        return None
    return {"delta": content, "chunk_kind": "buffered_final"}


def _emit_stream_event(event_name: str, event_payload: dict[str, Any]) -> None:
    writer = _require_stream_writer()
    writer(
        {
            "kind": "assistant_turn_tool_stream_event",
            "event_name": event_name,
            "event_payload": event_payload,
        }
    )


def _require_stream_writer() -> Callable[[dict[str, Any]], None]:
    writer = get_stream_writer()
    if writer is None:
        raise ConfigurationError(
            "Assistant turn tool stream runtime requires astream(stream_mode='custom') to emit events"
        )
    return writer


def _deserialize_stream_event(payload: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != "assistant_turn_tool_stream_event":
        return None
    event_name = payload.get("event_name")
    event_payload = payload.get("event_payload")
    if not isinstance(event_name, str) or not isinstance(event_payload, dict):
        return None
    return event_name, event_payload
