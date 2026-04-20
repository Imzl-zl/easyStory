from dataclasses import dataclass

import pytest

from app.modules.assistant.service.turn.assistant_turn_stream_execution_runtime import (
    LangGraphAssistantTurnStreamExecutionRuntime,
)
from app.shared.runtime.llm.llm_tool_provider import LLMStreamEvent


@dataclass(frozen=True)
class _FakeResponse:
    content: str

    def model_dump(self, *, mode: str) -> dict[str, str]:
        assert mode == "json"
        return {"content": self.content}


@pytest.mark.asyncio
async def test_assistant_turn_stream_execution_runtime_replays_completed_response() -> None:
    replayed_response = _FakeResponse("done")

    runtime = LangGraphAssistantTurnStreamExecutionRuntime(
        replayed_response=replayed_response,
        build_stream_event_data=lambda event_seq, extra=None: {
            "event_seq": event_seq,
            **(extra or {}),
        },
        run_started_extra={"requested_write_scope": "turn", "requested_write_targets": []},
        run_before_hooks=lambda: (_ for _ in ()).throw(AssertionError("before should not run")),
        should_stream_with_tool_loop=False,
        stream_tool_loop=_empty_stream_tool_loop,
        call_turn_llm_stream=_empty_llm_stream,
        finalize_response=lambda before_results, raw_output: (_ for _ in ()).throw(
            AssertionError("finalize should not run")
        ),
        run_prepared_on_error_hooks=lambda error: (_ for _ in ()).throw(
            AssertionError("error hooks should not run")
        ),
        store_terminal_turn=lambda **kwargs: _fail_async(
            AssertionError("store should not run for replayed completion")
        ),
        attach_stream_error_meta=lambda error, payload: (_ for _ in ()).throw(
            AssertionError("error meta should not attach")
        ),
    )

    events = [event async for event in runtime.iterate()]

    assert events == [
        (
            "run_started",
            {
                "event_seq": 1,
                "requested_write_scope": "turn",
                "requested_write_targets": [],
            },
        ),
        (
            "completed",
            {
                "event_seq": 2,
                "content": "done",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_stream_execution_runtime_streams_chunks_and_completed() -> None:
    call_log: list[object] = []

    async def call_turn_llm_stream():
        yield LLMStreamEvent(delta="one")
        yield LLMStreamEvent(delta="two")
        yield LLMStreamEvent(response={"content": "final"})

    async def finalize_response(before_results, raw_output):
        call_log.append(("finalize", before_results, raw_output))
        return _FakeResponse("final")

    async def store_terminal_turn(**kwargs):
        call_log.append(("store", kwargs))

    runtime = LangGraphAssistantTurnStreamExecutionRuntime(
        replayed_response=None,
        build_stream_event_data=lambda event_seq, extra=None: {
            "event_seq": event_seq,
            **(extra or {}),
        },
        run_started_extra={"requested_write_scope": "turn", "requested_write_targets": []},
        run_before_hooks=lambda: _return_async(["before"]),
        should_stream_with_tool_loop=False,
        stream_tool_loop=_empty_stream_tool_loop,
        call_turn_llm_stream=call_turn_llm_stream,
        finalize_response=finalize_response,
        run_prepared_on_error_hooks=lambda error: _return_async(None),
        store_terminal_turn=store_terminal_turn,
        attach_stream_error_meta=lambda error, payload: call_log.append(("error_meta", error, payload)),
    )

    events = [event async for event in runtime.iterate()]

    assert events == [
        (
            "run_started",
            {
                "event_seq": 1,
                "requested_write_scope": "turn",
                "requested_write_targets": [],
            },
        ),
        ("chunk", {"event_seq": 2, "delta": "one"}),
        ("chunk", {"event_seq": 3, "delta": "two"}),
        ("completed", {"event_seq": 4, "content": "final"}),
    ]
    assert call_log == [
        ("finalize", ["before"], {"content": "final"}),
        ("store", {"response": _FakeResponse("final")}),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_stream_execution_runtime_attaches_error_meta_on_finalize_failure() -> None:
    call_log: list[object] = []
    failure = RuntimeError("finalize failed")

    async def call_turn_llm_stream():
        yield LLMStreamEvent(delta="one")
        yield LLMStreamEvent(response={"content": "final"})

    async def finalize_response(before_results, raw_output):
        raise failure

    async def run_prepared_on_error_hooks(error: Exception):
        call_log.append(("error_hook", error))
        return None

    async def store_terminal_turn(**kwargs):
        call_log.append(("store", kwargs))

    def attach_stream_error_meta(error: Exception, payload: dict[str, object]):
        call_log.append(("error_meta", error, payload))

    runtime = LangGraphAssistantTurnStreamExecutionRuntime(
        replayed_response=None,
        build_stream_event_data=lambda event_seq, extra=None: {
            "event_seq": event_seq,
            **(extra or {}),
        },
        run_started_extra={"requested_write_scope": "turn", "requested_write_targets": []},
        run_before_hooks=lambda: _return_async(["before"]),
        should_stream_with_tool_loop=False,
        stream_tool_loop=_empty_stream_tool_loop,
        call_turn_llm_stream=call_turn_llm_stream,
        finalize_response=finalize_response,
        run_prepared_on_error_hooks=run_prepared_on_error_hooks,
        store_terminal_turn=store_terminal_turn,
        attach_stream_error_meta=attach_stream_error_meta,
    )

    with pytest.raises(RuntimeError, match="finalize failed"):
        [event async for event in runtime.iterate()]

    assert call_log == [
        ("error_hook", failure),
        ("store", {"error": failure}),
        ("error_meta", failure, {"event_seq": 3}),
    ]


async def _return_async(value):
    return value


async def _fail_async(error: Exception):
    raise error


async def _empty_llm_stream():
    if False:
        yield LLMStreamEvent(delta="unused")


async def _empty_stream_tool_loop():
    if False:
        yield ("unused", {})
