from __future__ import annotations

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    PROBE_TOOL_NAME,
    build_conformance_probe_request,
    build_tool_continuation_probe_followup_request,
    conformance_probe_kind_satisfies,
    normalize_conformance_probe_kind,
    promote_conformance_probe_kind,
    resolve_conformance_probe_kind_rank,
    validate_tool_call_probe_response,
    validate_tool_continuation_probe_response,
    validate_tool_definition_probe_response,
)
from app.shared.runtime.llm.llm_protocol import (
    LLMConnection,
    NormalizedLLMResponse,
)
from app.shared.runtime.llm.llm_protocol_types import NormalizedLLMToolCall


def test_normalize_conformance_probe_kind_defaults_to_text_probe() -> None:
    assert normalize_conformance_probe_kind(None) == "text_probe"


def test_normalize_conformance_probe_kind_rejects_unknown_value() -> None:
    with pytest.raises(ConfigurationError, match="Unsupported conformance probe kind"):
        normalize_conformance_probe_kind("unknown")


def test_resolve_conformance_probe_kind_rank_orders_tool_probes() -> None:
    assert resolve_conformance_probe_kind_rank(None) is None
    assert resolve_conformance_probe_kind_rank("text_probe") == 0
    assert resolve_conformance_probe_kind_rank("tool_definition_probe") == 1
    assert resolve_conformance_probe_kind_rank("tool_call_probe") == 2
    assert resolve_conformance_probe_kind_rank("tool_continuation_probe") == 3


def test_conformance_probe_kind_satisfies_requires_at_least_required_rank() -> None:
    assert conformance_probe_kind_satisfies(
        "tool_continuation_probe",
        required_probe_kind="tool_call_probe",
    ) is True
    assert conformance_probe_kind_satisfies(
        "tool_call_probe",
        required_probe_kind="tool_continuation_probe",
    ) is False
    assert conformance_probe_kind_satisfies(
        None,
        required_probe_kind="text_probe",
    ) is False


def test_promote_conformance_probe_kind_keeps_highest_verified_capability() -> None:
    assert promote_conformance_probe_kind(None, "text_probe") == "text_probe"
    assert (
        promote_conformance_probe_kind(
            "tool_continuation_probe",
            "text_probe",
        )
        == "tool_continuation_probe"
    )
    assert (
        promote_conformance_probe_kind(
            "tool_call_probe",
            "tool_continuation_probe",
        )
        == "tool_continuation_probe"
    )


def test_build_conformance_probe_request_uses_safe_tool_alias() -> None:
    request = build_conformance_probe_request(
        LLMConnection(
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-5.4",
        probe_kind="tool_call_probe",
    )

    assert request.json_body["tools"][0]["name"] == "probe_echo_payload"
    assert request.tool_name_aliases == {PROBE_TOOL_NAME: "probe_echo_payload"}


def test_build_tool_continuation_probe_followup_request_uses_provider_continuation_for_responses() -> None:
    request = build_tool_continuation_probe_followup_request(
        LLMConnection(
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-5.4",
        initial_response=_tool_call_response(provider_response_id="resp_123"),
    )

    assert request.json_body["previous_response_id"] == "resp_123"
    assert request.json_body["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": '{"echoed":"ping","ok":true,"probe":"tool_continuation_probe"}',
        }
    ]
    assert request.json_body["tools"][0]["name"] == "probe_echo_payload"


def test_build_tool_continuation_probe_followup_request_replays_for_chat_dialect() -> None:
    request = build_tool_continuation_probe_followup_request(
        LLMConnection(
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-5.4",
        initial_response=_tool_call_response(provider_response_id=None),
    )

    assert "previous_response_id" not in request.json_body
    assistant_tool_call_message = next(
        item for item in request.json_body["messages"] if item.get("role") == "assistant" and item.get("tool_calls")
    )
    tool_result_message = next(
        item for item in request.json_body["messages"] if item.get("role") == "tool"
    )
    assert assistant_tool_call_message["tool_calls"][0]["function"]["name"] == "probe_echo_payload"
    assert "probe_echo_payload" in tool_result_message["content"]


def test_build_tool_continuation_probe_followup_request_requires_response_id_for_responses() -> None:
    with pytest.raises(ConfigurationError, match="requires provider_response_id"):
        build_tool_continuation_probe_followup_request(
            LLMConnection(
                api_dialect="openai_responses",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-5.4",
            initial_response=_tool_call_response(provider_response_id=None),
        )


def test_validate_tool_definition_probe_response_requires_any_output() -> None:
    with pytest.raises(ConfigurationError, match="returned neither text nor tool calls"):
        validate_tool_definition_probe_response(
            NormalizedLLMResponse(
                content="",
                finish_reason=None,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
        )


def test_validate_tool_call_probe_response_rejects_wrong_arguments() -> None:
    with pytest.raises(ConfigurationError, match="expected arguments"):
        validate_tool_call_probe_response(
            _tool_call_response(arguments={"echo": "wrong"})
        )


def test_validate_tool_continuation_probe_response_requires_expected_echo() -> None:
    with pytest.raises(ConfigurationError, match="must mention 'ping'"):
        validate_tool_continuation_probe_response(
            NormalizedLLMResponse(
                content="工具续接成功",
                finish_reason=None,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
        )


def _tool_call_response(
    *,
    provider_response_id: str | None = "resp_123",
    arguments: dict[str, object] | None = None,
) -> NormalizedLLMResponse:
    return NormalizedLLMResponse(
        content="",
        finish_reason=None,
        input_tokens=8,
        output_tokens=10,
        total_tokens=18,
        provider_response_id=provider_response_id,
        tool_calls=[
            NormalizedLLMToolCall(
                tool_call_id="call_123",
                tool_name=PROBE_TOOL_NAME,
                arguments=arguments or {"echo": "ping"},
                arguments_text='{"echo":"ping"}',
            )
        ],
    )
