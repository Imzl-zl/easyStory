from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm_protocol import HttpJsonResponse
from app.shared.runtime.llm_tool_provider import LLMToolProvider
from app.shared.settings import ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV


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
