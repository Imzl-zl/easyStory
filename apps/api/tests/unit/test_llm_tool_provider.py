from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm_protocol import HttpJsonResponse
from app.shared.runtime.llm_tool_provider import LLMToolProvider


def test_execute_builds_openai_chat_request_with_default_model_fallback() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [{"message": {"content": "生成结果"}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                },
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "system_prompt": "你是助手",
                "model": {"provider": "openai"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "default_model": "gpt-4o-mini",
                },
            },
        )
    )

    request = captured["request"]
    assert request.url == "https://api.openai.com/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.json_body["model"] == "gpt-4o-mini"
    assert request.json_body["messages"] == [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "测试提示词"},
    ]
    assert result["model_name"] == "gpt-4o-mini"
    assert result["provider"] == "openai"
    assert result["content"] == "生成结果"


def test_execute_builds_openai_responses_request() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "output_text": "responses 结果",
                "usage": {"input_tokens": 8, "output_tokens": 10, "total_tokens": 18},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "写个摘要",
                "system_prompt": "保持简洁",
                "response_format": "json_object",
                "model": {"provider": "openai", "name": "gpt-4.1-mini", "max_tokens": 128},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_responses",
                },
            },
        )
    )

    request = captured["request"]
    assert request.url == "https://api.openai.com/v1/responses"
    assert request.json_body["model"] == "gpt-4.1-mini"
    assert request.json_body["instructions"] == "保持简洁"
    assert request.json_body["input"] == [{"role": "user", "content": "写个摘要"}]
    assert request.json_body["max_output_tokens"] == 128
    assert request.json_body["text"] == {"format": {"type": "json_object"}}
    assert result["content"] == "responses 结果"


def test_execute_builds_anthropic_messages_request() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "content": [{"type": "text", "text": "anthropic 结果"}],
                "usage": {"input_tokens": 20, "output_tokens": 30},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "续写一段",
                "system_prompt": "保持古风",
                "model": {
                    "provider": "anthropic",
                    "name": "claude-sonnet-4-20250514",
                    "temperature": 0.4,
                    "stop": ["END"],
                },
                "credential": {
                    "api_key": "anthropic-key",
                    "api_dialect": "anthropic_messages",
                },
            },
        )
    )

    request = captured["request"]
    assert request.url == "https://api.anthropic.com/v1/messages"
    assert request.headers["x-api-key"] == "anthropic-key"
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert request.json_body["system"] == [{"type": "text", "text": "保持古风"}]
    assert request.json_body["messages"] == [{"role": "user", "content": "续写一段"}]
    assert request.json_body["stop_sequences"] == ["END"]
    assert result["content"] == "anthropic 结果"
    assert result["total_tokens"] == 50


def test_execute_builds_gemini_generate_content_request() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "gemini 结果"}],
                        }
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 11,
                    "candidatesTokenCount": 22,
                    "totalTokenCount": 33,
                },
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "给个标题",
                "system_prompt": "中文输出",
                "response_format": "json_object",
                "model": {
                    "provider": "gemini",
                    "name": "gemini-2.5-pro",
                    "temperature": 0.3,
                    "max_tokens": 64,
                },
                "credential": {
                    "api_key": "gemini-key",
                    "api_dialect": "gemini_generate_content",
                },
            },
        )
    )

    request = captured["request"]
    assert request.url == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-pro:generateContent"
    )
    assert request.headers["x-goog-api-key"] == "gemini-key"
    assert request.json_body["system_instruction"] == {"parts": [{"text": "中文输出"}]}
    assert request.json_body["contents"] == [{"parts": [{"text": "给个标题"}]}]
    assert request.json_body["generationConfig"]["responseMimeType"] == "application/json"
    assert result["content"] == "gemini 结果"


def test_execute_allows_bearer_override_for_anthropic_messages() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "content": [{"type": "text", "text": "override 结果"}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试 override",
                "model": {"provider": "anthropic", "name": "claude-haiku"},
                "credential": {
                    "api_key": "anthropic-key",
                    "api_dialect": "anthropic_messages",
                    "auth_strategy": "bearer",
                },
            },
        )
    )

    request = captured["request"]
    assert request.headers["Authorization"] == "Bearer anthropic-key"
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert "x-api-key" not in request.headers
    assert result["content"] == "override 结果"


def test_execute_allows_custom_header_override_for_gemini() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "candidates": [{"content": {"parts": [{"text": "custom header 结果"}]}}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试 header",
                "model": {"provider": "gemini", "name": "gemini-flash-latest"},
                "credential": {
                    "api_key": "gemini-key",
                    "api_dialect": "gemini_generate_content",
                    "auth_strategy": "custom_header",
                    "api_key_header_name": "api-key",
                },
            },
        )
    )

    request = captured["request"]
    assert request.headers["api-key"] == "gemini-key"
    assert "x-goog-api-key" not in request.headers
    assert result["content"] == "custom header 结果"


def test_execute_merges_extra_headers_without_overriding_auth() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [{"message": {"content": "extra header 结果"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "带自定义头",
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "extra_headers": {"X-Trace-Id": "trace-001"},
                },
            },
        )
    )

    request = captured["request"]
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.headers["X-Trace-Id"] == "trace-001"
    assert result["content"] == "extra header 结果"


def test_execute_reports_gemini_finish_reason_when_response_has_no_parts() -> None:
    async def request_sender(_request):
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "candidates": [{"content": {}, "finishReason": "MAX_TOKENS"}],
                "usageMetadata": {"promptTokenCount": 1, "totalTokenCount": 1},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)

    with pytest.raises(ConfigurationError, match="finishReason=MAX_TOKENS"):
        asyncio.run(
            provider.execute(
                "llm.generate",
                {
                    "prompt": "测试 gemini 空响应",
                    "model": {"provider": "gemini", "name": "gemini-flash-latest"},
                    "credential": {
                        "api_key": "gemini-key",
                        "api_dialect": "gemini_generate_content",
                    },
                },
            )
        )


def test_execute_rejects_missing_model_name_and_default_model() -> None:
    provider = LLMToolProvider()

    with pytest.raises(ConfigurationError, match="missing executable model name"):
        asyncio.run(
            provider.execute(
                "llm.generate",
                {
                    "prompt": "测试提示词",
                    "model": {"provider": "openai"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_chat_completions",
                    },
                },
            )
        )
