from __future__ import annotations

import asyncio

import httpx
import pytest

from app.modules.credential.infrastructure import AsyncHttpCredentialVerifier
from app.shared.runtime.errors import BusinessRuleError
from app.shared.runtime.llm_protocol import HttpJsonResponse


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
        )
    )

    request = captured["request"]
    assert request.url == "https://proxy.example.com/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.json_body["model"] == "gpt-4o-mini"
    assert request.json_body["messages"][-1]["content"] == "Reply with ok."
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
