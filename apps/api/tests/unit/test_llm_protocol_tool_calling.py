from __future__ import annotations

import json

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm_protocol_requests import prepare_generation_request
from app.shared.runtime.llm_protocol_responses import parse_generation_response
from app.shared.runtime.llm_protocol_types import (
    LLMConnection,
    LLMFunctionToolDefinition,
    LLMGenerateRequest,
    allows_provider_continuation_state,
    resolve_continuation_support,
)


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


def test_prepare_generation_request_includes_openai_responses_tools() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_responses",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-4o-mini",
            prompt="读一下设定",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            tools=[
                LLMFunctionToolDefinition(
                    name="project.read_documents",
                    description="读取项目文稿。",
                    parameters={
                        "type": "object",
                        "properties": {
                            "paths": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["paths"],
                    },
                )
            ],
        )
    )

    assert request.json_body["tools"][0]["type"] == "function"
    assert request.json_body["tools"][0]["name"] == "project.read_documents"
    assert request.json_body["tools"][0]["strict"] is True
    assert request.json_body["parallel_tool_calls"] is False


def test_prepare_generation_request_uses_previous_response_id_for_openai_responses_continuation() -> None:
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
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_responses",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-4o-mini",
            prompt="先读一下人物设定。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            continuation_items=continuation_items,
            provider_continuation_state={
                "previous_response_id": "resp_prev_123",
                "latest_items": continuation_items,
            },
        )
    )

    assert request.json_body["previous_response_id"] == "resp_prev_123"
    assert request.json_body["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": '{"catalog_version":"catalog-v1","documents":[{"path":"设定/人物.md"}],"errors":[]}',
        }
    ]


def test_resolve_continuation_support_distinguishes_provider_continuation_and_runtime_replay() -> None:
    responses_support = resolve_continuation_support("openai_responses")
    anthropic_support = resolve_continuation_support("anthropic_messages")

    assert responses_support.continuation_mode == "hybrid"
    assert responses_support.tolerates_interleaved_tool_results is True
    assert responses_support.requires_full_replay_after_local_tools is False
    assert allows_provider_continuation_state(responses_support) is True
    assert anthropic_support.continuation_mode == "runtime_replay"
    assert anthropic_support.tolerates_interleaved_tool_results is False
    assert anthropic_support.requires_full_replay_after_local_tools is True
    assert allows_provider_continuation_state(anthropic_support) is False


def test_prepare_generation_request_falls_back_to_runtime_replay_for_anthropic() -> None:
    continuation_items = _build_runtime_replay_continuation_items()
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="anthropic_messages",
                api_key="test-key",
                base_url="https://api.anthropic.com",
            ),
            model_name="claude-sonnet-4-20250514",
            prompt="先读一下人物设定。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            continuation_items=continuation_items,
            provider_continuation_state={
                "previous_response_id": "resp_prev_123",
                "latest_items": continuation_items,
            },
        )
    )

    assert "previous_response_id" not in request.json_body
    assert request.json_body["messages"][0]["content"][0]["text"] == "先读一下人物设定。"
    assert request.json_body["messages"][1]["content"][0]["type"] == "tool_use"
    assert request.json_body["messages"][1]["content"][0]["name"] == "project.read_documents"
    assert request.json_body["messages"][2]["content"][0]["type"] == "tool_result"
    assert "设定/人物.md" in request.json_body["messages"][2]["content"][0]["content"]


def test_prepare_generation_request_falls_back_to_runtime_replay_for_openai_chat_completions() -> None:
    continuation_items = _build_runtime_replay_continuation_items()
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_chat_completions",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-4o-mini",
            prompt="先读一下人物设定。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            continuation_items=continuation_items,
            provider_continuation_state={
                "previous_response_id": "resp_prev_123",
                "latest_items": continuation_items,
            },
        )
    )

    assert "previous_response_id" not in request.json_body
    assert request.json_body["messages"][1] == {"role": "user", "content": "先读一下人物设定。"}
    assert request.json_body["messages"][2]["tool_calls"][0]["function"]["name"] == "project.read_documents"
    assert request.json_body["messages"][3]["role"] == "tool"
    assert "设定/人物.md" in request.json_body["messages"][3]["content"]


def test_prepare_generation_request_falls_back_to_runtime_replay_for_gemini() -> None:
    continuation_items = _build_runtime_replay_continuation_items()
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="gemini_generate_content",
                api_key="test-key",
                base_url="https://generativelanguage.googleapis.com",
            ),
            model_name="gemini-2.5-pro",
            prompt="先读一下人物设定。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            continuation_items=continuation_items,
            provider_continuation_state={
                "previous_response_id": "resp_prev_123",
                "latest_items": continuation_items,
            },
        )
    )

    assert "previous_response_id" not in request.json_body
    assert request.json_body["contents"][0]["parts"][0]["text"] == "先读一下人物设定。"
    assert (
        request.json_body["contents"][1]["parts"][0]["functionCall"]["name"]
        == "project.read_documents"
    )
    assert (
        request.json_body["contents"][2]["parts"][0]["functionResponse"]["name"]
        == "project.read_documents"
    )
    assert "设定/人物.md" in json.dumps(
        request.json_body["contents"][2]["parts"][0]["functionResponse"]["response"],
        ensure_ascii=False,
    )


def test_prepare_generation_request_rejects_mixed_openai_responses_continuation() -> None:
    with pytest.raises(
        ConfigurationError,
        match="OpenAI responses continuation requires tool_result items with call_id and structured_output",
    ):
        prepare_generation_request(
            LLMGenerateRequest(
                connection=LLMConnection(
                    api_dialect="openai_responses",
                    api_key="test-key",
                    base_url="https://api.openai.com",
                ),
                model_name="gpt-4o-mini",
                prompt="继续上一步。",
                system_prompt="你是小说助手。",
                response_format="text",
                temperature=None,
                max_tokens=256,
                top_p=None,
                continuation_items=[
                    {
                        "item_type": "tool_result",
                        "call_id": "call_123",
                        "payload": {"content_items": [{"type": "text", "text": "只有文本，没有 structured_output"}]},
                    }
                ],
                provider_continuation_state={
                    "previous_response_id": "resp_prev_123",
                    "latest_items": [
                        {
                            "item_type": "tool_result",
                            "call_id": "call_123",
                            "payload": {
                                "content_items": [
                                    {"type": "text", "text": "只有文本，没有 structured_output"}
                                ]
                            },
                        }
                    ],
                },
            )
        )


def test_parse_openai_responses_response_extracts_function_call() -> None:
    normalized = parse_generation_response(
        "openai_responses",
        {
            "id": "resp_123",
            "output": [
                {
                    "id": "fc_123",
                    "type": "function_call",
                    "call_id": "call_123",
                    "name": "project.read_documents",
                    "arguments": '{"paths":["设定/人物.md"]}',
                }
            ],
            "usage": {
                "input_tokens": 12,
                "output_tokens": 4,
                "total_tokens": 16,
            },
        },
    )

    assert normalized.content == ""
    assert normalized.provider_response_id == "resp_123"
    assert normalized.tool_calls[0].tool_call_id == "call_123"
    assert normalized.tool_calls[0].tool_name == "project.read_documents"
    assert normalized.tool_calls[0].arguments == {"paths": ["设定/人物.md"]}
    assert normalized.provider_output_items[0]["item_type"] == "tool_call"


def test_parse_openai_responses_response_rejects_invalid_tool_arguments_json() -> None:
    with pytest.raises(ConfigurationError, match="Tool call arguments JSON is invalid"):
        parse_generation_response(
            "openai_responses",
            {
                "id": "resp_bad",
                "output": [
                    {
                        "id": "fc_bad",
                        "type": "function_call",
                        "call_id": "call_bad",
                        "name": "project.read_documents",
                        "arguments": '{"paths":["设定/人物.md"]',
                    }
                ],
            },
        )
