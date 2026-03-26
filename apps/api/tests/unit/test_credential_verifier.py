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
        return HttpJsonResponse(status_code=200, json_body={"ok": True}, text="")

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
    assert result.message == "Credential verified"


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
        return HttpJsonResponse(status_code=200, json_body={"ok": True}, text="")

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
        return HttpJsonResponse(status_code=200, json_body={"ok": True}, text="")

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
