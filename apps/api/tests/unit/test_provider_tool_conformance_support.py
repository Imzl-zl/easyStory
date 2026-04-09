from __future__ import annotations

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    PROBE_TOOL_NAME,
    TOOL_DEFINITION_PROBE_SUCCESS_TEXT,
    build_conformance_probe_request,
    build_tool_continuation_probe_followup_request,
    conformance_probe_kind_satisfies,
    normalize_conformance_probe_kind,
    promote_conformance_probe_kind,
    render_tool_continuation_probe_success_text,
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
    assert request.json_body["tool_choice"] == "required"
    assert request.tool_name_aliases == {PROBE_TOOL_NAME: "probe_echo_payload"}


def test_build_conformance_probe_request_disables_gemini_probe_thinking() -> None:
    request = build_conformance_probe_request(
        LLMConnection(
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com",
        ),
        model_name="gemini-2.5-flash",
        probe_kind="tool_call_probe",
    )

    assert request.json_body["toolConfig"]["functionCallingConfig"] == {
        "mode": "ANY",
        "allowedFunctionNames": ["probe_echo_payload"],
    }
    assert request.json_body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
    assert request.tool_name_aliases == {PROBE_TOOL_NAME: "probe_echo_payload"}


def test_build_conformance_probe_request_forces_anthropic_tool_call() -> None:
    request = build_conformance_probe_request(
        LLMConnection(
            api_dialect="anthropic_messages",
            api_key="test-key",
            base_url="https://api.anthropic.com",
        ),
        model_name="claude-sonnet-4-20250514",
        probe_kind="tool_call_probe",
    )

    assert request.json_body["tool_choice"] == {
        "type": "any",
        "disable_parallel_tool_use": True,
    }


def test_build_tool_continuation_probe_followup_request_replays_for_default_responses_profile() -> None:
    request = build_tool_continuation_probe_followup_request(
        LLMConnection(
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-5.4",
        initial_response=_tool_call_response(provider_response_id="resp_123"),
        result_echo="probe-result-123",
    )

    assert "previous_response_id" not in request.json_body
    replay_prompt = request.json_body["input"][0]["content"][0]["text"]
    assert "probe-result-123" in replay_prompt
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
        result_echo="probe-result-456",
    )

    assert "previous_response_id" not in request.json_body
    assistant_tool_call_message = next(
        item for item in request.json_body["messages"] if item.get("role") == "assistant" and item.get("tool_calls")
    )
    tool_result_message = next(
        item for item in request.json_body["messages"] if item.get("role") == "tool"
    )
    followup_user_message = next(
        item
        for item in reversed(request.json_body["messages"])
        if item.get("role") == "user"
    )
    assert assistant_tool_call_message["tool_calls"][0]["function"]["name"] == "probe_echo_payload"
    assert "probe-result-456" in tool_result_message["content"]
    assert "probe-result-456" not in followup_user_message["content"]
    assert "ping" not in followup_user_message["content"]


def test_build_tool_continuation_probe_followup_request_exposes_echoed_value_for_gemini() -> None:
    request = build_tool_continuation_probe_followup_request(
        LLMConnection(
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com",
        ),
        model_name="gemini-2.5-flash",
        initial_response=_tool_call_response(provider_response_id=None),
        result_echo="probe-result-gemini",
    )

    followup_user_prompt = request.json_body["contents"][0]["parts"][0]["text"]
    response_payload = request.json_body["contents"][2]["parts"][0]["functionResponse"]["response"]

    assert response_payload["echoed"] == "probe-result-gemini"
    assert response_payload["structured_output"]["echoed"] == "probe-result-gemini"
    assert "probe-result-gemini" not in followup_user_prompt
    assert request.json_body["contents"][1]["parts"][0]["functionCall"]["name"] == "probe_echo_payload"
    assert request.json_body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
    assert request.tool_name_aliases == {PROBE_TOOL_NAME: "probe_echo_payload"}


def test_build_tool_continuation_probe_followup_request_preserves_gemini_provider_metadata() -> None:
    request = build_tool_continuation_probe_followup_request(
        LLMConnection(
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com",
        ),
        model_name="gemini-2.5-flash",
        initial_response=_tool_call_response(
            provider_response_id=None,
            provider_payload={
                "thoughtSignature": "sig_123",
                "functionCall": {
                    "id": "fn_123",
                    "name": "probe_echo_payload",
                    "args": {"echo": "ping"},
                },
            },
        ),
        result_echo="probe-result-gemini",
    )

    assert request.json_body["contents"][1]["parts"][0]["thoughtSignature"] == "sig_123"
    assert request.json_body["contents"][1]["parts"][0]["functionCall"]["id"] == "fn_123"
    assert request.json_body["contents"][2]["parts"][0]["functionResponse"]["id"] == "fn_123"


def test_build_tool_continuation_probe_followup_request_uses_provider_continuation_for_responses_strict() -> None:
    request = build_tool_continuation_probe_followup_request(
        LLMConnection(
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com",
            interop_profile="responses_strict",
        ),
        model_name="gpt-5.4",
        initial_response=_tool_call_response(provider_response_id="resp_123"),
        result_echo="probe-result-strict",
    )

    assert request.json_body["previous_response_id"] == "resp_123"
    assert request.json_body["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": '{"echoed":"probe-result-strict","ok":true,"probe":"tool_continuation_probe"}',
        }
    ]


def test_build_tool_continuation_probe_followup_request_requires_response_id_for_responses_strict() -> None:
    with pytest.raises(ConfigurationError, match="requires provider_response_id"):
        build_tool_continuation_probe_followup_request(
            LLMConnection(
                api_dialect="openai_responses",
                api_key="test-key",
                base_url="https://api.openai.com",
                interop_profile="responses_strict",
            ),
            model_name="gpt-5.4",
            initial_response=_tool_call_response(provider_response_id=None),
        )


def test_validate_tool_definition_probe_response_requires_exact_success_text() -> None:
    with pytest.raises(ConfigurationError, match="must return exactly"):
        validate_tool_definition_probe_response(
            NormalizedLLMResponse(
                content="我不能使用工具。",
                finish_reason=None,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
        )
    validate_tool_definition_probe_response(
        NormalizedLLMResponse(
            content=f"  {TOOL_DEFINITION_PROBE_SUCCESS_TEXT}  ",
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


def test_validate_tool_continuation_probe_response_requires_dynamic_echo_in_final_text() -> None:
    with pytest.raises(ConfigurationError, match="must include echoed value"):
        validate_tool_continuation_probe_response(
            NormalizedLLMResponse(
                content="工具续接成功，但没有带回工具结果。",
                finish_reason=None,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            ),
            expected_echo="ping",
        )
    validate_tool_continuation_probe_response(
        NormalizedLLMResponse(
            content=f"收到结果，{render_tool_continuation_probe_success_text('probe-result-789')}",
            finish_reason=None,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
        ),
        expected_echo="probe-result-789",
    )


def _tool_call_response(
    *,
    provider_response_id: str | None = "resp_123",
    arguments: dict[str, object] | None = None,
    provider_payload: dict[str, object] | None = None,
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
                provider_payload=provider_payload,
            )
        ],
    )
