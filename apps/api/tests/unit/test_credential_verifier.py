from __future__ import annotations

import asyncio

import httpx
import pytest

from app.modules.credential.infrastructure import AsyncHttpCredentialVerifier
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm_protocol import (
    NormalizedLLMResponse,
    VERIFY_SYSTEM_PROMPT,
    VERIFY_USER_PROMPT,
)
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
            auth_strategy="custom_header",
            api_key_header_name="api-key",
            extra_headers={"X-Trace-Id": "trace-verify"},
        )
    )

    request = captured["request"]
    assert request.url == "https://proxy.example.com/v1/chat/completions"
    assert request.headers["Accept"] == "text/event-stream"
    assert request.headers["api-key"] == "test-key"
    assert request.headers["X-Trace-Id"] == "trace-verify"
    assert request.json_body["model"] == "gpt-4o-mini"
    assert request.json_body["stream"] is True
    assert request.json_body["messages"][-1]["content"] == VERIFY_USER_PROMPT
    assert request.json_body["messages"][0]["content"] == VERIFY_SYSTEM_PROMPT
    assert captured["api_dialect"] == "openai_chat_completions"
    assert result.message == "验证成功"


def test_verify_credential_rejects_probe_content_mismatch() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        return _ok_response("Gemini 3 Pro is no longer available.")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="验证响应不匹配"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
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
    assert captured["api_dialect"] == "openai_responses"
    assert result.message == "验证成功"


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
