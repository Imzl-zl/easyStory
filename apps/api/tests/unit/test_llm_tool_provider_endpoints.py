from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol import HttpJsonResponse
from app.shared.runtime.llm.llm_tool_provider import LLMToolProvider
from app.shared.settings import (
    ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV,
    ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
    clear_settings_cache,
)


def test_execute_keeps_full_openai_endpoint_without_duplicate_join() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": "生成结果"}}]},
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "base_url": "https://proxy.example.com/openai/v1/chat/completions",
                },
            },
        )
    )

    assert captured["request"].url == "https://proxy.example.com/openai/v1/chat/completions"


def test_execute_rejects_private_base_url_by_default() -> None:
    provider = LLMToolProvider()

    with pytest.raises(ConfigurationError, match="Private or local model endpoints are disabled"):
        asyncio.run(
            provider.execute(
                "llm.generate",
                {
                    "prompt": "测试提示词",
                    "model": {"provider": "openai", "name": "gpt-4o-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_chat_completions",
                        "base_url": "http://127.0.0.1:11434/v1",
                    },
                },
            )
        )


def test_execute_rejects_public_http_base_url_by_default(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV, "false")
    clear_settings_cache()
    provider = LLMToolProvider()

    try:
        with pytest.raises(ConfigurationError, match="Public http model endpoints are disabled"):
            asyncio.run(
                provider.execute(
                    "llm.generate",
                    {
                        "prompt": "测试提示词",
                        "model": {"provider": "openai", "name": "gpt-4o-mini"},
                        "credential": {
                            "api_key": "test-key",
                            "api_dialect": "openai_chat_completions",
                            "base_url": "http://49.234.21.84:3000/v1",
                        },
                    },
                )
            )
    finally:
        clear_settings_cache()


def test_execute_allows_private_base_url_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "true")
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": "本地结果"}}]},
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "base_url": "http://127.0.0.1:11434/v1",
                },
            },
        )
    )

    assert captured["request"].url == "http://127.0.0.1:11434/v1/chat/completions"
    assert result["content"] == "本地结果"


def test_execute_allows_public_http_base_url_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV, "true")
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": "公网结果"}}]},
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "base_url": "http://49.234.21.84:3000/v1",
                },
            },
        )
    )

    assert captured["request"].url == "http://49.234.21.84:3000/v1/chat/completions"
    assert result["content"] == "公网结果"


def test_execute_keeps_full_anthropic_endpoint_with_bearer_override() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={"content": [{"type": "text", "text": "代理结果"}]},
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "anthropic", "name": "claude-haiku"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "anthropic_messages",
                    "auth_strategy": "bearer",
                    "base_url": "https://proxy.example.com/v1/messages",
                },
            },
        )
    )

    request = captured["request"]
    assert request.url == "https://proxy.example.com/v1/messages"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.headers["anthropic-version"] == "2023-06-01"
