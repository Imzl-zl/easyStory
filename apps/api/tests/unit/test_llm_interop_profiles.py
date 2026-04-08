from __future__ import annotations

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_interop_profiles import (
    resolve_interop_capabilities,
)
from app.shared.runtime.llm.llm_stream_events import parse_raw_stream_event


def test_resolve_interop_capabilities_uses_declared_default_profile() -> None:
    responses_capabilities = resolve_interop_capabilities("openai_responses")
    chat_capabilities = resolve_interop_capabilities("openai_chat_completions")
    anthropic_capabilities = resolve_interop_capabilities("anthropic_messages")
    gemini_capabilities = resolve_interop_capabilities("gemini_generate_content")

    assert responses_capabilities.profile == "responses_delta_first_terminal_empty_output"
    assert responses_capabilities.allows_responses_empty_output_in_stream_terminal is True
    assert responses_capabilities.supports_provider_response_continuation is False
    assert responses_capabilities.tool_name_policy == "safe_ascii_only"
    assert responses_capabilities.tool_schema_mode == "openai_strict_compatible"
    assert chat_capabilities.profile == "chat_compat_plain"
    assert chat_capabilities.captures_chat_reasoning_content is False
    assert chat_capabilities.tool_name_policy == "safe_ascii_only"
    assert chat_capabilities.tool_schema_mode == "openai_strict_compatible"
    assert anthropic_capabilities.profile is None
    assert anthropic_capabilities.tool_schema_mode == "portable_subset"
    assert gemini_capabilities.profile is None
    assert gemini_capabilities.tool_schema_mode == "gemini_compatible"


def test_resolve_interop_capabilities_keeps_provider_continuation_for_responses_strict() -> None:
    capabilities = resolve_interop_capabilities("openai_responses", "responses_strict")

    assert capabilities.supports_provider_response_continuation is True
    assert capabilities.tool_schema_mode == "openai_strict_compatible"


def test_resolve_interop_capabilities_rejects_incompatible_profile() -> None:
    with pytest.raises(ConfigurationError, match="只支持 responses_strict"):
        resolve_interop_capabilities(
            "openai_responses",
            "chat_compat_plain",
        )


def test_parse_raw_stream_event_extracts_reasoning_delta_for_reasoning_profile() -> None:
    event = parse_raw_stream_event(
        "openai_chat_completions",
        event_name=None,
        payload={
            "choices": [
                {
                    "delta": {
                        "content": "结论",
                        "reasoning_content": [{"text": "先分析一下"}],
                    }
                }
            ]
        },
        interop_profile="chat_compat_reasoning_content",
    )

    assert event.delta == "结论"
    assert event.reasoning_delta == "先分析一下"


def test_parse_raw_stream_event_ignores_reasoning_delta_for_plain_chat_profile() -> None:
    event = parse_raw_stream_event(
        "openai_chat_completions",
        event_name=None,
        payload={
            "choices": [
                {
                    "delta": {
                        "content": "结论",
                        "reasoning_content": "先分析一下",
                    }
                }
            ]
        },
        interop_profile="chat_compat_plain",
    )

    assert event.delta == "结论"
    assert event.reasoning_delta == ""


def test_parse_raw_stream_event_decodes_terminal_tool_name_alias() -> None:
    event = parse_raw_stream_event(
        "openai_responses",
        event_name="response.completed",
        payload={
            "type": "response.completed",
            "response": {
                "id": "resp_tool_1",
                "output": [
                    {
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
    assert event.terminal_response.tool_calls[0].tool_name == "project.read_documents"
