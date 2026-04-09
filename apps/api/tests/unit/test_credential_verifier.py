from __future__ import annotations

import asyncio
import re

import app.modules.credential.infrastructure.verifier as verifier_module
import httpx
import pytest

from app.modules.credential.infrastructure import AsyncHttpCredentialVerifier
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_stream_support import ParsedStreamEvent
from app.shared.runtime.llm.llm_protocol import (
    HttpJsonResponse,
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


def test_verify_credential_text_probe_returns_after_first_stream_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_iterate_stream_request(*_args, **_kwargs):
        yield ParsedStreamEvent(
            event_name="content_block_delta",
            payload={},
            delta="我",
        )
        raise AssertionError("text probe should stop after first non-empty delta")

    monkeypatch.setattr(
        verifier_module,
        "iterate_stream_request",
        fake_iterate_stream_request,
    )

    verifier = AsyncHttpCredentialVerifier()
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
            client_name="easyStory",
        )
    )

    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_text_probe_accepts_terminal_response_without_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_iterate_stream_request(*_args, **_kwargs):
        yield ParsedStreamEvent(
            event_name="response.completed",
            payload={},
            delta="",
            terminal_response=_ok_response("今天天气真好。"),
        )

    monkeypatch.setattr(
        verifier_module,
        "iterate_stream_request",
        fake_iterate_stream_request,
    )

    verifier = AsyncHttpCredentialVerifier()
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-4.1-mini",
            client_name="easyStory",
        )
    )

    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_text_probe_uses_json_request_for_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_send_json_http_request(request, *, timeout_seconds):
        captured["request"] = request
        captured["timeout_seconds"] = timeout_seconds
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "content": [{"type": "text", "text": "今天天气真好。"}],
                "id": "msg_123",
                "model": "claude-sonnet-4.6",
                "role": "assistant",
                "stop_reason": "end_turn",
                "type": "message",
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
            text='{"content":[{"type":"text","text":"今天天气真好。"}]}',
        )

    async def unexpected_iterate_stream_request(*_args, **_kwargs):
        raise AssertionError("anthropic text probe should use plain JSON request")
        yield  # pragma: no cover

    monkeypatch.setattr(
        verifier_module,
        "send_json_http_request",
        fake_send_json_http_request,
    )
    monkeypatch.setattr(
        verifier_module,
        "iterate_stream_request",
        unexpected_iterate_stream_request,
    )

    verifier = AsyncHttpCredentialVerifier()
    result = asyncio.run(
        verifier.verify(
            provider="claude",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="anthropic_messages",
            default_model="claude-sonnet-4-6",
            client_name="easyStory",
        )
    )

    request = captured["request"]
    assert request.url == "https://proxy.example.com/v1/messages"
    assert "stream" not in request.json_body
    assert captured["timeout_seconds"] == verifier_module.VERIFY_TEXT_PROBE_TIMEOUT_SECONDS
    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_text_probe_rejects_truncated_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_send_json_http_request(_request, *, timeout_seconds):
        assert timeout_seconds == verifier_module.VERIFY_TEXT_PROBE_TIMEOUT_SECONDS
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "content": [{"type": "text", "text": "只返回了半截"}],
                "id": "msg_123",
                "model": "claude-sonnet-4.6",
                "role": "assistant",
                "stop_reason": "max_tokens",
                "type": "message",
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
            text='{"content":[{"type":"text","text":"只返回了半截"}]}',
        )

    monkeypatch.setattr(
        verifier_module,
        "send_json_http_request",
        fake_send_json_http_request,
    )

    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="上游在输出尚未完成时提前停止了这次回复"):
        asyncio.run(
            verifier.verify(
                provider="claude",
                api_key="test-key",
                base_url="https://proxy.example.com",
                api_dialect="anthropic_messages",
                default_model="claude-sonnet-4-6",
                client_name="easyStory",
            )
        )


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


def test_verify_credential_surfaces_empty_tool_response_protocol_error() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        raise ConfigurationError(
            "当前连接在启用工具时返回了空响应：既没有文本，也没有工具调用。"
            "这通常表示该连接当前不支持所选协议下的工具调用。"
            "请重新执行“验证工具”，或切换可稳定支持工具调用的连接。"
        )

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="启用工具时返回了空响应"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                probe_kind="tool_continuation_probe",
                transport_mode="stream",
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
    assert request.json_body["generationConfig"] == {
        "temperature": 0.0,
        "maxOutputTokens": 256,
        "topP": 1.0,
    }
    assert "thinkingConfig" not in request.json_body["generationConfig"]
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
        prompt_text = request.json_body["input"][0]["content"][0]["text"]
        matched = re.search(r'"echoed":"(probe-result-[^"]+)"', prompt_text)
        assert matched is not None
        echoed = matched.group(1)
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
            transport_mode="stream",
            client_name="easyStory",
        )
    )

    assert len(captured_requests) == 2
    assert captured_requests[0].json_body["tools"][0]["name"] == "probe_echo_payload"
    assert "previous_response_id" not in captured_requests[1].json_body
    followup_input = captured_requests[1].json_body["input"]
    assert len(followup_input) == 1
    assert followup_input[0]["role"] == "user"
    prompt_text = followup_input[0]["content"][0]["text"]
    assert "probe-result-" in prompt_text
    assert result.message == "流式工具调用验证成功"
    assert result.probe_kind == "tool_continuation_probe"
    assert result.transport_mode == "stream"


def test_verify_tool_probe_requires_transport_mode() -> None:
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="工具验证必须显式指定 transport_mode"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_responses",
                default_model="gpt-5.4",
                probe_kind="tool_continuation_probe",
            )
        )


def test_verify_text_probe_rejects_transport_mode() -> None:
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="验证连接时不支持 transport_mode"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                transport_mode="stream",
            )
        )


def test_verify_buffered_tool_probe_uses_json_request_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_requests: list[PreparedLLMHttpRequest] = []

    async def fake_send_json_http_request(request, *, timeout_seconds):
        captured_requests.append(request)
        assert timeout_seconds == verifier_module.VERIFY_TIMEOUT_SECONDS
        if len(captured_requests) == 1:
            return HttpJsonResponse(
                status_code=200,
                json_body={
                    "id": "resp_1",
                    "output": [
                        {
                            "type": "function_call",
                            "id": "fc_1",
                            "call_id": "call_123",
                            "name": "probe_echo_payload",
                            "arguments": '{"echo":"ping"}',
                        }
                    ],
                    "usage": {"input_tokens": 8, "output_tokens": 10, "total_tokens": 18},
                },
                text='{"id":"resp_1"}',
            )
        prompt_text = request.json_body["input"][0]["content"][0]["text"]
        matched = re.search(r'"echoed":"(probe-result-[^"]+)"', prompt_text)
        assert matched is not None
        echoed = matched.group(1)
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "id": "resp_2",
                "output": [
                    {
                        "id": "msg_1",
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": f"工具续接成功：{echoed}。",
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 6, "output_tokens": 4, "total_tokens": 10},
            },
            text='{"id":"resp_2"}',
        )

    async def unexpected_iterate_stream_request(*_args, **_kwargs):
        raise AssertionError("buffered tool probe should not use stream transport")
        yield  # pragma: no cover

    monkeypatch.setattr(
        verifier_module,
        "send_json_http_request",
        fake_send_json_http_request,
    )
    monkeypatch.setattr(
        verifier_module,
        "iterate_stream_request",
        unexpected_iterate_stream_request,
    )

    verifier = AsyncHttpCredentialVerifier()
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-5.4",
            probe_kind="tool_continuation_probe",
            transport_mode="buffered",
            client_name="easyStory",
        )
    )

    assert len(captured_requests) == 2
    assert captured_requests[0].json_body.get("stream") in {None, False}
    assert captured_requests[1].json_body.get("stream") in {None, False}
    assert result.message == "非流工具调用验证成功"
    assert result.probe_kind == "tool_continuation_probe"
    assert result.transport_mode == "buffered"


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
