from __future__ import annotations

import asyncio
import json

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol import HttpJsonResponse
from app.shared.runtime.llm.llm_tool_provider import LLMStreamEvent, LLMToolProvider


def _build_runtime_replay_continuation_items() -> list[dict[str, object]]:
    return [
        {
            "item_type": "tool_call",
            "call_id": "call_123",
            "payload": {
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物.md"]},
                "arguments_text": '{"paths":["设定/人物.md"]}',
                "tool_call_id": "call_123",
            },
        },
        {
            "item_type": "tool_result",
            "call_id": "call_123",
            "status": "completed",
            "tool_name": "project.read_documents",
            "payload": {
                "tool_name": "project.read_documents",
                "structured_output": {
                    "documents": [{"path": "设定/人物.md"}],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                "content_items": [{"type": "text", "text": "设定/人物.md\n\n林渊"}],
            },
        },
    ]


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


def test_execute_rejects_empty_tool_response_when_tools_enabled() -> None:
    async def request_sender(_request):
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [
                    {
                        "message": {"role": "assistant"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 4,
                    "total_tokens": 16,
                },
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)

    with pytest.raises(ConfigurationError, match="启用工具时返回了空响应"):
        asyncio.run(
            provider.execute(
                "llm.generate",
                {
                    "prompt": "测试提示词",
                    "model": {"provider": "openai", "name": "gpt-4o-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_chat_completions",
                    },
                    "tools": [
                        {
                            "name": "project.read_documents",
                            "description": "读取文稿。",
                            "parameters": {
                                "type": "object",
                                "properties": {"paths": {"type": "array"}},
                                "required": ["paths"],
                            },
                        }
                    ],
                },
            )
        )


def test_execute_rejects_openai_responses_empty_output_text_without_output_items() -> None:
    async def request_sender(_request):
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "output_text": "",
                "output": [],
                "usage": {
                    "input_tokens": 12,
                    "output_tokens": 4,
                    "total_tokens": 16,
                },
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)

    with pytest.raises(ConfigurationError, match="output must be a non-empty list"):
        asyncio.run(
            provider.execute(
                "llm.generate",
                {
                    "prompt": "测试提示词",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                },
            )
        )


def test_execute_falls_back_to_credential_default_max_output_tokens() -> None:
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
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "default_max_output_tokens": 2048,
                },
            },
        )
    )

    assert captured["request"].json_body["max_completion_tokens"] == 2048


def test_execute_rejects_invalid_provider_native_reasoning_for_runtime_request() -> None:
    provider = LLMToolProvider()

    with pytest.raises(
        ConfigurationError,
        match="thinking_level and thinking_budget are only valid for Gemini native requests",
    ):
        asyncio.run(
            provider.execute(
                "llm.generate",
                {
                    "prompt": "测试提示词",
                    "model": {
                        "provider": "openai",
                        "name": "gpt-5.4",
                        "thinking_budget": 0,
                    },
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_chat_completions",
                    },
                },
            )
        )


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
    assert request.json_body["input"] == [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "写个摘要"}],
        }
    ]
    assert request.json_body["max_output_tokens"] == 128
    assert request.json_body["text"] == {"format": {"type": "json_object"}}
    assert result["content"] == "responses 结果"


def test_execute_omits_openai_responses_max_output_tokens_without_overrides() -> None:
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
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "写个摘要",
                "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_responses",
                },
            },
        )
    )

    assert "max_output_tokens" not in captured["request"].json_body


def test_execute_uses_conservative_anthropic_max_tokens_when_no_override_exists() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "生成结果"}],
                "model": "claude-sonnet-4",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 12, "output_tokens": 34},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "anthropic", "name": "claude-sonnet-4"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "anthropic_messages",
                },
            },
        )
    )

    assert captured["request"].json_body["max_tokens"] == 8192


def test_execute_clamps_anthropic_default_max_tokens_to_context_window() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "生成结果"}],
                "model": "claude-sonnet-4",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 12, "output_tokens": 34},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "anthropic", "name": "claude-sonnet-4"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "anthropic_messages",
                    "context_window_tokens": 4096,
                },
            },
        )
    )

    assert captured["request"].json_body["max_tokens"] == 4095
def test_execute_builds_openai_responses_runtime_replay_continuation_request() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "output_text": "继续推理后的结果",
                "usage": {"input_tokens": 6, "output_tokens": 8, "total_tokens": 14},
            },
            text="",
        )

    continuation_items = [
        {
            "item_type": "tool_result",
            "call_id": "call_123",
            "payload": {
                "structured_output": {
                    "documents": [{"path": "设定/人物.md"}],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                }
            },
        }
    ]
    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "先读一下人物设定。",
                "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_responses",
                },
                "tools": [
                    {
                        "name": "project.read_documents",
                        "description": "读取项目文稿。",
                        "parameters": {
                            "type": "object",
                            "properties": {"paths": {"type": "array"}},
                            "required": ["paths"],
                        },
                    }
                ],
                "continuation_items": continuation_items,
                "provider_continuation_state": {
                    "previous_response_id": "resp_prev_123",
                    "latest_items": continuation_items,
                },
            },
        )
    )

    request = captured["request"]
    assert "previous_response_id" not in request.json_body
    assert request.json_body["input"][0]["role"] == "user"
    assert "设定/人物.md" in request.json_body["input"][0]["content"][0]["text"]
    assert request.json_body["tools"][0]["strict"] is True


def test_execute_builds_openai_responses_provider_continuation_request_for_strict_profile() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "output_text": "继续推理后的结果",
                "usage": {"input_tokens": 6, "output_tokens": 8, "total_tokens": 14},
            },
            text="",
        )

    continuation_items = [
        {
            "item_type": "tool_result",
            "call_id": "call_123",
            "payload": {
                "structured_output": {
                    "documents": [{"path": "设定/人物.md"}],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                }
            },
        }
    ]
    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "先读一下人物设定。",
                "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_responses",
                    "interop_profile": "responses_strict",
                },
                "tools": [
                    {
                        "name": "project.read_documents",
                        "description": "读取项目文稿。",
                        "parameters": {
                            "type": "object",
                            "properties": {"paths": {"type": "array"}},
                            "required": ["paths"],
                        },
                    }
                ],
                "continuation_items": continuation_items,
                "provider_continuation_state": {
                    "previous_response_id": "resp_prev_123",
                    "latest_items": continuation_items,
                },
            },
        )
    )

    request = captured["request"]
    assert request.json_body["previous_response_id"] == "resp_prev_123"
    assert request.json_body["input"][0]["type"] == "function_call_output"


def test_execute_discards_provider_continuation_state_for_runtime_replay_dialect() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "content": [{"type": "text", "text": "anthropic 续接结果"}],
                "usage": {"input_tokens": 10, "output_tokens": 6},
            },
            text="",
        )

    continuation_items = _build_runtime_replay_continuation_items()
    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "先读一下人物设定。",
                "model": {"provider": "anthropic", "name": "claude-sonnet-4-20250514"},
                "credential": {
                    "api_key": "anthropic-key",
                    "api_dialect": "anthropic_messages",
                },
                "continuation_items": continuation_items,
                "provider_continuation_state": {
                    "previous_response_id": "resp_prev_123",
                    "latest_items": continuation_items,
                },
            },
        )
    )

    request = captured["request"]
    assert "previous_response_id" not in request.json_body
    assert request.json_body["messages"][0]["content"][0]["text"] == "先读一下人物设定。"
    assert request.json_body["messages"][1]["content"][0]["type"] == "tool_use"
    assert request.json_body["messages"][2]["content"][0]["type"] == "tool_result"
    assert "设定/人物.md" in request.json_body["messages"][2]["content"][0]["content"]
    assert result["content"] == "anthropic 续接结果"


@pytest.mark.parametrize(
    ("api_dialect", "provider_name", "model_name", "expected_content"),
    [
        ("openai_chat_completions", "openai", "gpt-4o-mini", "openai chat 续接结果"),
        ("gemini_generate_content", "gemini", "gemini-2.5-pro", "gemini 续接结果"),
    ],
)
def test_execute_discards_provider_continuation_state_for_other_runtime_replay_dialects(
    api_dialect: str,
    provider_name: str,
    model_name: str,
    expected_content: str,
) -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        if api_dialect == "openai_chat_completions":
            return HttpJsonResponse(
                status_code=200,
                json_body={
                    "choices": [{"message": {"content": expected_content}}],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 6,
                        "total_tokens": 16,
                    },
                },
                text="",
            )
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "candidates": [{"content": {"parts": [{"text": expected_content}]}}],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 6,
                    "totalTokenCount": 16,
                },
            },
            text="",
        )

    continuation_items = _build_runtime_replay_continuation_items()
    provider = LLMToolProvider(request_sender=request_sender)
    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "先读一下人物设定。",
                "model": {"provider": provider_name, "name": model_name},
                "credential": {
                    "api_key": f"{provider_name}-key",
                    "api_dialect": api_dialect,
                },
                "continuation_items": continuation_items,
                "provider_continuation_state": {
                    "previous_response_id": "resp_prev_123",
                    "latest_items": continuation_items,
                },
            },
        )
    )

    request = captured["request"]
    assert "previous_response_id" not in request.json_body
    if api_dialect == "openai_chat_completions":
        assert request.json_body["messages"][0] == {"role": "user", "content": "先读一下人物设定。"}
        request_text = request.json_body["messages"][2]["content"]
    else:
        assert request.json_body["contents"][0]["parts"][0]["text"] == "先读一下人物设定。"
        request_text = json.dumps(
            request.json_body["contents"][2]["parts"][0]["functionResponse"]["response"],
            ensure_ascii=False,
        )
    assert "设定/人物.md" in request_text
    assert result["content"] == expected_content


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
    assert request.json_body["messages"] == [
        {
            "role": "user",
            "content": [{"type": "text", "text": "续写一段"}],
        }
    ]
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
    assert request.json_body["contents"] == [{"role": "user", "parts": [{"text": "给个标题"}]}]
    assert request.json_body["generationConfig"]["responseMimeType"] == "application/json"
    assert result["content"] == "gemini 结果"


def test_execute_sanitizes_gemini_tool_schema_before_sending() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "candidates": [{"content": {"parts": [{"text": "gemini 工具结果"}]}}],
                "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 3, "totalTokenCount": 5},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "读取当前文稿",
                "model": {
                    "provider": "gemini",
                    "name": "gemini-2.5-pro",
                },
                "credential": {
                    "api_key": "gemini-key",
                    "api_dialect": "gemini_generate_content",
                },
                "tools": [
                    {
                        "name": "project.read_documents",
                        "description": "读取项目文稿。",
                        "parameters": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "paths": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "options": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {"mode": {"type": "string"}},
                                },
                            },
                            "anyOf": [
                                {"required": ["paths"]},
                                {"required": ["options"]},
                            ],
                            "required": ["paths"],
                        },
                    }
                ],
            },
        )
    )

    params = captured["request"].json_body["tools"][0]["functionDeclarations"][0]["parameters"]
    assert params == {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
            },
            "options": {
                "type": "object",
                "properties": {"mode": {"type": "string"}},
            },
        },
        "description": "Provide at least one of: options, paths.",
        "required": ["paths"],
    }


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


def test_execute_builds_user_agent_from_client_identity() -> None:
    captured = {}

    async def request_sender(request):
        captured["request"] = request
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "choices": [{"message": {"content": "ua 结果"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)
    asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "看下 UA",
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "client_name": "easyStory",
                    "client_version": "0.1",
                    "runtime_kind": "server-python",
                },
            },
        )
    )

    request = captured["request"]
    assert request.headers["User-Agent"] == "easyStory/0.1 (server; python)"


def test_execute_prefers_user_agent_override_over_client_identity() -> None:
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
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "openai_chat_completions",
                    "user_agent_override": "codex-cli/0.118.0 (server; node)",
                    "client_name": "easyStory",
                    "client_version": "0.1",
                    "runtime_kind": "server-python",
                },
            },
        )
    )

    request = captured["request"]
    assert request.headers["User-Agent"] == "codex-cli/0.118.0 (server; node)"
    assert result["content"] == "生成结果"


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

    with pytest.raises(ConfigurationError, match="上游在输出尚未完成时提前停止了这次回复"):
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


def test_execute_stream_yields_chunks_and_completed_result(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"有新方向"}'
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"output":[{"type":"message",'
                '"content":[{"type":"output_text","text":"今天有新方向"}]}]}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "给个方向",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert [event.delta for event in events[:-1]] == ["今天", "有新方向"]
    assert events[-1].response == {
        "content": "今天有新方向",
        "finish_reason": None,
        "model_name": "gpt-4.1-mini",
        "provider": "openai",
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "tool_calls": [],
        "provider_response_id": None,
        "output_items": [
            {
                "item_type": "text",
                "item_id": "provider:openai_responses:text:1",
                "status": "completed",
                "provider_ref": None,
                "payload": {"content": "今天有新方向", "phase": "final"},
            }
        ],
    }


def test_execute_stream_uses_openai_completed_payload_when_no_deltas(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"output":[{"type":"message",'
                '"content":[{"type":"output_text","text":"今天有新方向"}]}],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "给个方向",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert events == [
        LLMStreamEvent(
            response={
                "content": "今天有新方向",
                "finish_reason": None,
                "model_name": "gpt-4.1-mini",
                "provider": "openai",
                "input_tokens": 8,
                "output_tokens": 10,
                "total_tokens": 18,
                "tool_calls": [],
                "provider_response_id": None,
                "output_items": [
                    {
                        "item_type": "text",
                        "item_id": "provider:openai_responses:text:1",
                        "status": "completed",
                        "provider_ref": None,
                        "payload": {"content": "今天有新方向", "phase": "final"},
                    }
                ],
            }
        )
    ]


def test_execute_stream_accepts_openai_completed_payload_with_tool_calls_and_no_text(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_tool_1","output":[{"type":"function_call",'
                '"call_id":"call_123","name":"project.read_documents","arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "读一下人物设定",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert events == [
        LLMStreamEvent(
            response={
                "content": "",
                "finish_reason": None,
                "model_name": "gpt-4.1-mini",
                "provider": "openai",
                "input_tokens": 8,
                "output_tokens": 10,
                "total_tokens": 18,
                "tool_calls": [
                    {
                        "tool_call_id": "call_123",
                        "tool_name": "project.read_documents",
                        "arguments": {"paths": ["设定/人物.md"]},
                        "arguments_text": '{"paths":["设定/人物.md"]}',
                        "provider_ref": None,
                    }
                ],
                "provider_response_id": "resp_tool_1",
                "output_items": [
                    {
                        "item_type": "tool_call",
                        "item_id": "provider:openai_responses:tool_call:1",
                        "status": "completed",
                        "provider_ref": None,
                        "call_id": "call_123",
                        "payload": {
                            "tool_name": "project.read_documents",
                            "arguments": {"paths": ["设定/人物.md"]},
                            "arguments_text": '{"paths":["设定/人物.md"]}',
                            "tool_call_id": "call_123",
                        },
                    }
                ],
            }
        )
    ]


def test_execute_stream_accepts_openai_completed_payload_with_empty_output_and_deltas(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"有新方向"}'
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_delta_first","output":[],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "给个方向",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert [event.delta for event in events[:-1]] == ["今天", "有新方向"]
    assert events[-1].response == {
        "content": "今天有新方向",
        "finish_reason": None,
        "model_name": "gpt-4.1-mini",
        "provider": "openai",
        "input_tokens": 8,
        "output_tokens": 10,
        "total_tokens": 18,
        "tool_calls": [],
        "provider_response_id": "resp_delta_first",
        "output_items": [],
    }


def test_execute_stream_recovers_openai_responses_tool_calls_from_output_item_events(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_item.done"
            yield (
                'data: {"type":"response.output_item.done","item":{"id":"fc_123","type":"function_call",'
                '"call_id":"call_123","name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}}'
            )
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_tool_delta","output":[],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "读一下人物设定",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                    "tools": [
                        {
                            "name": "project.read_documents",
                            "description": "读取文稿。",
                            "parameters": {
                                "type": "object",
                                "properties": {"paths": {"type": "array"}},
                                "required": ["paths"],
                            },
                        }
                    ],
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert len(events) == 1
    response = events[0].response
    assert response is not None
    assert response["content"] == ""
    assert response["provider_response_id"] == "resp_tool_delta"
    assert response["input_tokens"] == 8
    assert response["output_tokens"] == 10
    assert response["total_tokens"] == 18
    assert response["tool_calls"] == [
        {
            "tool_call_id": "call_123",
            "tool_name": "project.read_documents",
            "arguments": {"paths": ["设定/人物.md"]},
            "arguments_text": '{"paths":["设定/人物.md"]}',
            "provider_ref": "fc_123",
        }
    ]
    assert response["output_items"] == [
        {
            "item_type": "tool_call",
            "item_id": "provider:openai_responses:tool_call:1",
            "status": "completed",
            "provider_ref": "fc_123",
            "call_id": "call_123",
            "payload": {
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物.md"]},
                "arguments_text": '{"paths":["设定/人物.md"]}',
                "tool_call_id": "call_123",
            },
        }
    ]


def test_execute_stream_recovers_openai_responses_tool_calls_from_argument_events(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.function_call_arguments.delta"
            yield 'data: {"type":"response.function_call_arguments.delta","item_id":"fc_123","output_index":0,"delta":"{\\"paths\\":["}'
            yield ""
            yield "event: response.function_call_arguments.done"
            yield (
                'data: {"type":"response.function_call_arguments.done","item_id":"fc_123","output_index":0,'
                '"call_id":"call_123","name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}'
            )
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_tool_delta_args","output":[],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "读一下人物设定",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                    "tools": [
                        {
                            "name": "project.read_documents",
                            "description": "读取文稿。",
                            "parameters": {
                                "type": "object",
                                "properties": {"paths": {"type": "array"}},
                                "required": ["paths"],
                            },
                        }
                    ],
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert len(events) == 1
    response = events[0].response
    assert response is not None
    assert response["provider_response_id"] == "resp_tool_delta_args"
    assert response["tool_calls"] == [
        {
            "tool_call_id": "call_123",
            "tool_name": "project.read_documents",
            "arguments": {"paths": ["设定/人物.md"]},
            "arguments_text": '{"paths":["设定/人物.md"]}',
            "provider_ref": "fc_123",
        }
    ]


def test_execute_stream_deduplicates_openai_responses_tool_calls_across_call_id_and_item_id(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.function_call_arguments.done"
            yield (
                'data: {"type":"response.function_call_arguments.done","call_id":"call_123","name":"project_read_documents",'
                '"arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}","output_index":0}'
            )
            yield ""
            yield "event: response.output_item.done"
            yield (
                'data: {"type":"response.output_item.done","output_index":0,"item":{"id":"fc_123","type":"function_call",'
                '"call_id":"call_123","name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}}'
            )
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_tool_mixed_keys","output":[{"id":"rs_1","type":"reasoning","summary":[]}],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "读一下人物设定",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                    "tools": [
                        {
                            "name": "project.read_documents",
                            "description": "读取文稿。",
                            "parameters": {
                                "type": "object",
                                "properties": {"paths": {"type": "array"}},
                                "required": ["paths"],
                            },
                        }
                    ],
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert len(events) == 1
    response = events[0].response
    assert response is not None
    assert response["provider_response_id"] == "resp_tool_mixed_keys"
    assert len(response["tool_calls"]) == 1
    assert response["tool_calls"][0] == {
        "tool_call_id": "call_123",
        "tool_name": "project.read_documents",
        "arguments": {"paths": ["设定/人物.md"]},
        "arguments_text": '{"paths":["设定/人物.md"]}',
        "provider_ref": "fc_123",
    }
    assert [item["item_type"] for item in response["output_items"]] == [
        "tool_call",
        "reasoning",
    ]


def test_execute_stream_preserves_openai_responses_output_order_for_multiple_missing_tool_calls(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.function_call_arguments.done"
            yield (
                'data: {"type":"response.function_call_arguments.done","item_id":"fc_1","call_id":"call_1",'
                '"name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物-1.md\\"]}","output_index":0}'
            )
            yield ""
            yield "event: response.function_call_arguments.done"
            yield (
                'data: {"type":"response.function_call_arguments.done","item_id":"fc_2","call_id":"call_2",'
                '"name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物-2.md\\"]}","output_index":2}'
            )
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_tool_ordered","output":[{"id":"msg_1","type":"message","role":"assistant",'
                '"content":[{"type":"output_text","text":"先看第一份，再补第二份。"}]},{"id":"rs_1","type":"reasoning","summary":[]}],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "先后读取两份人物设定",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                    "tools": [
                        {
                            "name": "project.read_documents",
                            "description": "读取文稿。",
                            "parameters": {
                                "type": "object",
                                "properties": {"paths": {"type": "array"}},
                                "required": ["paths"],
                            },
                        }
                    ],
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert len(events) == 1
    response = events[0].response
    assert response is not None
    assert response["provider_response_id"] == "resp_tool_ordered"
    assert [item["item_type"] for item in response["output_items"]] == [
        "tool_call",
        "text",
        "tool_call",
        "reasoning",
    ]
    assert [
        item.get("provider_ref")
        for item in response["output_items"]
        if item["item_type"] == "tool_call"
    ] == ["fc_1", "fc_2"]


def test_execute_stream_recovers_openai_chat_tool_calls_from_delta_events(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield (
                'data: {"id":"chatcmpl_123","choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_123",'
                '"type":"function","function":{"name":"project_read_documents","arguments":""}}],"role":"assistant"},'
                '"finish_reason":null}]}'
            )
            yield ""
            yield (
                'data: {"id":"chatcmpl_123","choices":[{"delta":{"tool_calls":[{"index":0,"function":'
                '{"arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}}]},"finish_reason":null}]}'
            )
            yield ""
            yield 'data: {"id":"chatcmpl_123","choices":[{"delta":{},"finish_reason":"tool_calls"}]}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "读一下人物设定",
                    "model": {"provider": "openai", "name": "gpt-5.4"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_chat_completions",
                    },
                    "tools": [
                        {
                            "name": "project.read_documents",
                            "description": "读取文稿。",
                            "parameters": {
                                "type": "object",
                                "properties": {"paths": {"type": "array"}},
                                "required": ["paths"],
                            },
                        }
                    ],
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert len(events) == 1
    response = events[0].response
    assert response is not None
    assert response["content"] == ""
    assert response["finish_reason"] == "tool_calls"
    assert response["tool_calls"] == [
        {
            "tool_call_id": "call_123",
            "tool_name": "project.read_documents",
            "arguments": {"paths": ["设定/人物.md"]},
            "arguments_text": '{"paths":["设定/人物.md"]}',
            "provider_ref": None,
        }
    ]
    assert response["output_items"] == [
        {
            "item_type": "tool_call",
            "item_id": "provider:openai_chat:tool_call:1",
            "status": "completed",
            "provider_ref": None,
            "call_id": "call_123",
            "payload": {
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物.md"]},
                "arguments_text": '{"paths":["设定/人物.md"]}',
                "tool_call_id": "call_123",
            },
        }
    ]


def test_execute_stream_rejects_openai_empty_output_with_strict_interop_profile(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.completed"
            yield 'data: {"type":"response.completed","response":{"id":"resp_strict","output":[]}}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "给个方向",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                        "interop_profile": "responses_strict",
                    },
                },
            )
        ]

    with pytest.raises(ConfigurationError, match="output must be a non-empty list"):
        asyncio.run(collect_events())


def test_execute_stream_rejects_empty_tool_response_when_tools_enabled(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield (
                'data: {"id":"chatcmpl_123","choices":[{"delta":{"role":"assistant"},'
                '"finish_reason":null}]}'
            )
            yield ""
            yield 'data: {"id":"chatcmpl_123","choices":[{"delta":{},"finish_reason":"stop"}]}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "测试提示词",
                    "model": {"provider": "openai", "name": "gpt-4o-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_chat_completions",
                    },
                    "tools": [
                        {
                            "name": "project.read_documents",
                            "description": "读取文稿。",
                            "parameters": {
                                "type": "object",
                                "properties": {"paths": {"type": "array"}},
                                "required": ["paths"],
                            },
                        }
                    ],
                },
            )
        ]

    with pytest.raises(ConfigurationError, match="启用工具时返回了空响应"):
        asyncio.run(collect_events())


def test_execute_stream_rejects_openai_terminal_content_conflict(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天有新方向"}'
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"output":[{"type":"message",'
                '"content":[{"type":"output_text","text":"明天改方向"}]}]}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "给个方向",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_responses",
                    },
                },
            )
        ]

    with pytest.raises(ConfigurationError, match="流式终态文本与已累计的增量文本不一致"):
        asyncio.run(collect_events())


def test_execute_stream_accepts_gemini_terminal_payload_with_tool_calls_and_no_text(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield (
                'data: {"candidates":[{"content":{"parts":[{"functionCall":{'
                '"name":"project.read_documents","args":{"paths":["设定/人物.md"]}}}],"role":"model"},'
                '"finishReason":"STOP"}],"usageMetadata":{"promptTokenCount":8,'
                '"candidatesTokenCount":10,"totalTokenCount":18}}'
            )
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "读一下人物设定",
                    "model": {"provider": "gemini", "name": "gemini-2.5-pro"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "gemini_generate_content",
                    },
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert events == [
        LLMStreamEvent(
            response={
                "content": "",
                "finish_reason": "STOP",
                "model_name": "gemini-2.5-pro",
                "provider": "gemini",
                "input_tokens": 8,
                "output_tokens": 10,
                "total_tokens": 18,
                    "tool_calls": [
                        {
                            "tool_call_id": "provider:gemini_generate_content:tool_call:1",
                            "tool_name": "project.read_documents",
                            "arguments": {"paths": ["设定/人物.md"]},
                            "arguments_text": '{"paths":["设定/人物.md"]}',
                            "provider_ref": None,
                            "provider_payload": {
                                "functionCall": {
                                    "name": "project.read_documents",
                                    "args": {"paths": ["设定/人物.md"]},
                                }
                            },
                        }
                    ],
                "provider_response_id": None,
                "output_items": [],
            }
        )
    ]


def test_execute_stream_raises_when_upstream_reports_truncation(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"今天"},"finish_reason":null}]}'
            yield ""
            yield 'data: {"choices":[{"delta":{"content":"还有后续"},"finish_reason":"length"}]}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_parts():
        parts: list[str] = []
        with pytest.raises(
            ConfigurationError,
            match="上游在输出尚未完成时提前停止了这次回复",
        ):
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "给个方向",
                    "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "openai_chat_completions",
                    },
                },
            ):
                if event.delta:
                    parts.append(event.delta)
        return parts

    assert asyncio.run(collect_parts()) == ["今天", "还有后续"]
