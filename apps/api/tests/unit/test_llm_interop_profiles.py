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

    assert responses_capabilities.profile == "responses_delta_first_terminal_empty_output"
    assert responses_capabilities.allows_responses_empty_output_in_stream_terminal is True
    assert chat_capabilities.profile == "chat_compat_plain"
    assert chat_capabilities.captures_chat_reasoning_content is False


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
