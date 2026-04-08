from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.modules.credential.infrastructure import AsyncHttpCredentialVerifier
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.llm_protocol import (
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
    VERIFY_SYSTEM_PROMPT,
    VERIFY_USER_PROMPT,
)
from app.shared.runtime.llm.llm_protocol_types import NormalizedLLMToolCall
from app.shared.settings import (
    ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV,
    ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
    clear_settings_cache,
)


def _ok_response(
    content: str,
    *,
    input_tokens: int = 1,
    output_tokens: int = 1,
    total_tokens: int = 2,
) -> NormalizedLLMResponse:
    return NormalizedLLMResponse(
        content=content,
        finish_reason=None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def test_verify_credential_uses_generation_probe_request() -> None:
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
            interop_profile="chat_compat_reasoning_content",
            auth_strategy="custom_header",
            api_key_header_name="api-key",
            extra_headers={"X-Trace-Id": "trace-verify"},
            user_agent_override=None,
            client_name="easyStory",
            client_version="0.1",
            runtime_kind="server-python",
        )
    )

    request = captured["request"]
    assert request.url == "https://proxy.example.com/v1/chat/completions"
    assert request.headers["Accept"] == "text/event-stream"
    assert request.headers["api-key"] == "test-key"
    assert request.headers["X-Trace-Id"] == "trace-verify"
    assert request.headers["User-Agent"] == "easyStory/0.1 (server; python)"
    assert request.interop_profile == "chat_compat_reasoning_content"
    assert request.json_body["model"] == "gpt-4o-mini"
    assert request.json_body["stream"] is True
    assert request.json_body["messages"][-1]["content"] == VERIFY_USER_PROMPT
    assert request.json_body["messages"][0]["content"] == VERIFY_SYSTEM_PROMPT
    assert captured["api_dialect"] == "openai_chat_completions"
    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_accepts_non_exact_probe_reply() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        return _ok_response("今天天气真好。\n补充一句说明也没关系。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url=None,
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
            client_name="easyStory",
        )
    )

    assert result.message == "验证成功"


def test_verify_credential_rejects_empty_probe_content() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        return _ok_response("   ")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="测试消息没有返回可用内容"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_credential_rejects_retired_model_message() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        return _ok_response("Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro.")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="当前默认模型已不可用"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_credential_rejects_model_configuration_error_message() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        return _ok_response("MEDIUM is not supported for this model.")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="默认模型或接口类型不匹配"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_credential_surfaces_stream_protocol_error() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        raise ConfigurationError("模型没有返回可展示的内容，请稍后重试。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="模型没有返回可展示的内容，请稍后重试"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_openai_responses_uses_input_text_blocks() -> None:
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-4.1-mini",
            user_agent_override="codex-cli/0.118.0 (server; node)",
            client_name="easyStory",
        )
    )

    request = captured["request"]
    assert request.json_body["input"] == [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": VERIFY_USER_PROMPT}],
        }
    ]
    assert request.json_body["instructions"] == VERIFY_SYSTEM_PROMPT
    assert request.json_body["stream"] is True
    assert request.headers["User-Agent"] == "codex-cli/0.118.0 (server; node)"
    assert captured["api_dialect"] == "openai_responses"
    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_gemini_request_includes_user_role_and_prompt() -> None:
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。", input_tokens=6, output_tokens=4, total_tokens=10)

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    result = asyncio.run(
        verifier.verify(
            provider="gemini",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="gemini_generate_content",
            default_model="gemini-2.5-pro",
            client_name="easyStory",
        )
    )

    request = captured["request"]
    assert request.url == (
        "https://proxy.example.com/v1beta/models/gemini-2.5-pro:streamGenerateContent?alt=sse"
    )
    assert request.headers["Accept"] == "text/event-stream"
    assert request.json_body["contents"] == [
        {"role": "user", "parts": [{"text": VERIFY_USER_PROMPT}]},
    ]
    assert "stream" not in request.json_body
    assert request.json_body["system_instruction"] == {
        "parts": [{"text": VERIFY_SYSTEM_PROMPT}],
    }
    assert request.json_body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
    assert captured["api_dialect"] == "gemini_generate_content"
    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_tool_continuation_probe_replays_followup_request() -> None:
    captured_requests: list[PreparedLLMHttpRequest] = []

    async def stream_request_sender(request, *, api_dialect):
        captured_requests.append(request)
        assert api_dialect == "openai_responses"
        if len(captured_requests) == 1:
            return NormalizedLLMResponse(
                content="",
                finish_reason=None,
                input_tokens=8,
                output_tokens=10,
                total_tokens=18,
                provider_response_id="resp_123",
                tool_calls=[
                    NormalizedLLMToolCall(
                        tool_call_id="call_123",
                        tool_name="probe.echo_payload",
                        arguments={"echo": "ping"},
                        arguments_text='{"echo":"ping"}',
                    )
                ],
            )
        output_payload = json.loads(request.json_body["input"][0]["output"])
        echoed = output_payload["echoed"]
        assert echoed.startswith("probe-result-")
        assert echoed != "ping"
        return _ok_response(
            f"工具续接成功：{echoed}。",
            input_tokens=6,
            output_tokens=4,
            total_tokens=10,
        )

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-5.4",
            probe_kind="tool_continuation_probe",
            client_name="easyStory",
        )
    )

    assert len(captured_requests) == 2
    assert captured_requests[0].json_body["tools"][0]["name"] == "probe_echo_payload"
    assert captured_requests[1].json_body["previous_response_id"] == "resp_123"
    followup_input = captured_requests[1].json_body["input"]
    assert len(followup_input) == 1
    assert followup_input[0]["type"] == "function_call_output"
    assert followup_input[0]["call_id"] == "call_123"
    assert json.loads(followup_input[0]["output"])["echoed"].startswith("probe-result-")
    assert result.message == "工具调用验证成功"
    assert result.probe_kind == "tool_continuation_probe"


def test_verify_credential_maps_authentication_error() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        raise ConfigurationError("LLM streaming request failed: HTTP 401 - bad key")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="API Key 无效"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                client_name="easyStory",
            )
        )


def test_verify_credential_surfaces_connection_error() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        raise httpx.ConnectError("connect failed")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="无法连接到 openai"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                client_name="easyStory",
            )
        )


def test_verify_credential_requires_executable_model_name() -> None:
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="missing executable model name"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model=None,
            )
        )


def test_verify_credential_rejects_private_base_url_by_default(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "false")
    clear_settings_cache()
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="Private or local model endpoints are disabled"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url="http://127.0.0.1:11434/v1",
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
            )
        )


def test_verify_credential_rejects_public_http_base_url_by_default(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV, "false")
    clear_settings_cache()
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="Public http model endpoints are disabled"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url="http://49.234.21.84:3000/v1",
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
            )
        )


def test_verify_credential_allows_private_base_url_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "true")
    clear_settings_cache()
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="http://127.0.0.1:11434/v1",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
        )
    )

    request = captured["request"]
    assert request.url == "http://127.0.0.1:11434/v1/chat/completions"
    assert request.json_body["stream"] is True
    assert captured["api_dialect"] == "openai_chat_completions"


def test_verify_credential_allows_public_http_base_url_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV, "true")
    clear_settings_cache()
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="http://49.234.21.84:3000/v1",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
        )
    )

    request = captured["request"]
    assert request.url == "http://49.234.21.84:3000/v1/chat/completions"
    assert request.json_body["stream"] is True
    assert captured["api_dialect"] == "openai_chat_completions"
