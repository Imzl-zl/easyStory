import pytest

from app.modules.assistant.service.turn import assistant_turn_tool_stream_runtime as runtime_module
from app.shared.runtime.errors import ConfigurationError


def test_emit_stream_event_requires_custom_langgraph_stream_context(monkeypatch) -> None:
    monkeypatch.setattr(runtime_module, "get_stream_writer", lambda: None)

    with pytest.raises(
        ConfigurationError,
        match="requires astream\\(stream_mode='custom'\\) to emit events",
    ):
        runtime_module._emit_stream_event("chunk", {"delta": "hi"})


def test_emit_stream_event_writes_payload_to_stream_writer(monkeypatch) -> None:
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(runtime_module, "get_stream_writer", lambda: captured.append)

    runtime_module._emit_stream_event("chunk", {"delta": "hi"})

    assert captured == [
        {
            "kind": "assistant_turn_tool_stream_event",
            "event_name": "chunk",
            "event_payload": {"delta": "hi"},
        }
    ]
