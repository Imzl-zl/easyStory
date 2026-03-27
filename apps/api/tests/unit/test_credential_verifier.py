from __future__ import annotations

import asyncio

import httpx
import pytest

from app.modules.credential.infrastructure import AsyncHttpCredentialVerifier
from app.shared.runtime.errors import BusinessRuleError
from app.shared.runtime.llm_protocol import HttpJsonResponse
from app.shared.settings import (
    ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV,
    ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
)


def test_verify_credential_uses_generation_probe_request() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [
                    {
                        "message": {
                            "content": "今天天气真好。",
                        }
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            text="",
        )

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)
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
    assert request.headers["api-key"] == "test-key"
    assert request.headers["X-Trace-Id"] == "trace-verify"
    assert request.json_body["model"] == "gpt-4o-mini"
    assert request.json_body["messages"][-1]["content"] == "今天天气真好。"
    assert result.message == "验证成功"


def test_verify_credential_rejects_probe_content_mismatch() -> None:
    async def request_sender(_request):
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [
                    {
                        "message": {
                            "content": "Gemini 3 Pro is no longer available.",
                        }
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            text="",
        )

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)

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


def test_verify_credential_rejects_non_json_response_payload() -> None:
    async def request_sender(_request):
        return HttpJsonResponse(status_code=200, json_body=None, text="ok")

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)

    with pytest.raises(BusinessRuleError, match="验证响应不是合法 JSON"):
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
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "output_text": "今天天气真好。",
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            },
            text="",
        )

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-4.1-mini",
        )
    )

    assert captured["request"].json_body["input"] == [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "今天天气真好。"}],
        }
    ]
    assert result.message == "验证成功"


def test_verify_gemini_request_includes_user_role_and_prompt() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "candidates": [{"content": {"parts": [{"text": "今天天气真好。"}]}}],
                "usageMetadata": {"promptTokenCount": 6, "candidatesTokenCount": 4, "totalTokenCount": 10},
            },
            text="",
        )

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)
    result = asyncio.run(
        verifier.verify(
            provider="gemini",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="gemini_generate_content",
            default_model="gemini-2.5-pro",
        )
    )

    assert captured["request"].json_body["contents"] == [
        {"role": "user", "parts": [{"text": "今天天气真好。"}]},
    ]
    assert captured["request"].json_body["system_instruction"] == {
        "parts": [{"text": "请直接回复这句话本身，不要添加额外内容。"}],
    }
    assert result.message == "验证成功"

def test_verify_credential_maps_authentication_error() -> None:
    async def request_sender(_request):
        return HttpJsonResponse(status_code=401, json_body={"error": "bad key"}, text="bad key")

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)

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
    async def request_sender(_request):
        raise httpx.ConnectError("connect failed")

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)

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


def test_verify_credential_rejects_private_base_url_by_default() -> None:
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


def test_verify_credential_rejects_public_http_base_url_by_default() -> None:
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
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [{"message": {"content": "今天天气真好。"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            text="",
        )

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)
    asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="http://127.0.0.1:11434/v1",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
        )
    )

    assert captured["request"].url == "http://127.0.0.1:11434/v1/chat/completions"


def test_verify_credential_allows_public_http_base_url_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV, "true")
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [{"message": {"content": "今天天气真好。"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            text="",
        )

    verifier = AsyncHttpCredentialVerifier(request_sender=request_sender)
    asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="http://49.234.21.84:3000/v1",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
        )
    )

    assert captured["request"].url == "http://49.234.21.84:3000/v1/chat/completions"
