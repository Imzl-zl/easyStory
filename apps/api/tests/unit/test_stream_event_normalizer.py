from __future__ import annotations

from app.shared.runtime.llm.interop.stream_event_normalizer import (
    build_truncated_stream_message,
    extract_stream_truncation_reason,
    parse_raw_stream_event,
)


def test_parse_raw_stream_event_extracts_openai_responses_delta_only() -> None:
    event = parse_raw_stream_event(
        "openai_responses",
        event_name="response.output_text.delta",
        payload={"delta": "今天"},
    )

    assert event.delta == "今天"
    assert event.stop_reason is None
    assert event.terminal_response is None


def test_parse_raw_stream_event_builds_openai_responses_terminal_response() -> None:
    event = parse_raw_stream_event(
        "openai_responses",
        event_name="response.completed",
        payload={
            "type": "response.completed",
            "response": {
                "id": "resp_123",
                "output": [
                    {
                        "id": "fc_123",
                        "type": "function_call",
                        "call_id": "call_123",
                        "name": "project_read_documents",
                        "arguments": '{"paths":["设定/人物.md"]}',
                    }
                ],
                "usage": {"input_tokens": 8, "output_tokens": 10, "total_tokens": 18},
            },
        },
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert event.terminal_response is not None
    assert event.terminal_response.provider_response_id == "resp_123"
    assert event.terminal_response.tool_calls[0].tool_name == "project.read_documents"
    assert event.terminal_response.tool_calls[0].provider_ref == "fc_123"


def test_parse_raw_stream_event_keeps_gemini_partial_payload_non_terminal() -> None:
    event = parse_raw_stream_event(
        "gemini_generate_content",
        event_name=None,
        payload={
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "只收到半句"}],
                    }
                }
            ]
        },
    )

    assert event.delta == "只收到半句"
    assert event.stop_reason is None
    assert event.terminal_response is not None
    assert event.terminal_response.finish_reason is None


def test_extract_stream_truncation_reason_normalizes_known_values() -> None:
    assert extract_stream_truncation_reason("length") == "length"
    assert extract_stream_truncation_reason("MAX_TOKENS") == "MAX_TOKENS"
    assert extract_stream_truncation_reason("stop") is None


def test_build_truncated_stream_message_includes_stop_reason() -> None:
    assert "stop_reason=MAX_TOKENS" in build_truncated_stream_message("MAX_TOKENS")
