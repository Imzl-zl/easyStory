from __future__ import annotations

import json

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_interop_profiles import resolve_connection_continuation_support
from app.shared.runtime.llm.llm_protocol_requests import prepare_generation_request
from app.shared.runtime.llm.llm_protocol_responses import (
    extract_response_truncation_reason,
    parse_generation_response,
    parse_stream_terminal_response,
)
from app.shared.runtime.llm.llm_protocol_types import (
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
    assert request.json_body["tools"][0]["name"] == "project_read_documents"
    assert request.json_body["tools"][0]["strict"] is True
    assert request.json_body["parallel_tool_calls"] is False
    assert request.tool_name_aliases == {"project.read_documents": "project_read_documents"}


def test_prepare_generation_request_forces_tool_call_for_openai_responses() -> None:
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
            force_tool_call=True,
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

    assert request.json_body["tool_choice"] == "required"


def test_prepare_generation_request_includes_openai_chat_reasoning_effort() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_chat_completions",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-5.4",
            prompt="读取文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            reasoning_effort="high",
        )
    )

    assert request.json_body["reasoning_effort"] == "high"
    assert request.json_body["max_completion_tokens"] == 256
    assert "max_tokens" not in request.json_body


def test_prepare_generation_request_uses_compat_max_tokens_for_custom_openai_chat_gateway() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_chat_completions",
                api_key="test-key",
                base_url="https://gateway.example.com/v1",
            ),
            model_name="gpt-5.4",
            prompt="读取文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            reasoning_effort="high",
        )
    )

    assert request.json_body["reasoning_effort"] == "high"
    assert request.json_body["max_tokens"] == 256
    assert "max_completion_tokens" not in request.json_body


def test_prepare_generation_request_uses_official_openai_token_field_for_openai_host_even_with_custom_provider_name() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                provider="new_api",
                api_dialect="openai_chat_completions",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-5.4",
            prompt="读取文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            reasoning_effort="high",
        )
    )

    assert request.json_body["max_completion_tokens"] == 256
    assert "max_tokens" not in request.json_body


def test_prepare_generation_request_allows_openai_reasoning_without_model_specific_matrix() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_chat_completions",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-5.1",
            prompt="读取文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            reasoning_effort="minimal",
        )
    )

    assert request.json_body["reasoning_effort"] == "minimal"


def test_prepare_generation_request_rejects_gemini_native_reasoning_on_openai_dialect() -> None:
    with pytest.raises(
        ConfigurationError,
        match="thinking_level and thinking_budget are only valid for Gemini native requests",
    ):
        prepare_generation_request(
            LLMGenerateRequest(
                connection=LLMConnection(
                    api_dialect="openai_chat_completions",
                    api_key="test-key",
                    base_url="https://api.openai.com",
                ),
                model_name="claude-sonnet-4",
                prompt="读取文稿。",
                system_prompt="你是小说助手。",
                response_format="text",
                temperature=None,
                max_tokens=256,
                top_p=None,
                thinking_level="low",
            )
        )


def test_prepare_generation_request_includes_openai_responses_reasoning_object() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_responses",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-5.4",
            prompt="读一下设定",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            reasoning_effort="none",
        )
    )

    assert request.json_body["reasoning"] == {"effort": "none"}


def test_prepare_generation_request_includes_gemini_thinking_level() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="gemini_generate_content",
                api_key="test-key",
                base_url="https://generativelanguage.googleapis.com",
            ),
            model_name="gemini-3-flash-preview",
            prompt="读取文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            thinking_level="low",
        )
    )

    assert request.json_body["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}


def test_prepare_generation_request_includes_gemini_thinking_budget() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="gemini_generate_content",
                api_key="test-key",
                base_url="https://generativelanguage.googleapis.com",
            ),
            model_name="gemini-2.5-flash",
            prompt="读取文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            thinking_budget=0,
        )
    )

    assert request.json_body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_prepare_generation_request_rejects_gemini_native_reasoning_effort() -> None:
    with pytest.raises(
        ConfigurationError,
        match="reasoning_effort is not valid for Gemini native requests",
    ):
        prepare_generation_request(
            LLMGenerateRequest(
                connection=LLMConnection(
                    api_dialect="gemini_generate_content",
                    api_key="test-key",
                    base_url="https://generativelanguage.googleapis.com",
                ),
                model_name="gemini-2.5-flash",
                prompt="读取文稿。",
                system_prompt="你是小说助手。",
                response_format="text",
                temperature=None,
                max_tokens=256,
                top_p=None,
                reasoning_effort="high",
            )
        )


def test_prepare_generation_request_compiles_portable_tool_schema_for_openai_responses() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_responses",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-4o-mini",
            prompt="检索文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            tools=[
                LLMFunctionToolDefinition(
                    name="project.search_documents",
                    description="检索项目文稿。",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "minLength": 1},
                            "path_prefix": {"type": "string", "minLength": 1},
                        },
                        "anyOf": [
                            {"required": ["query"]},
                            {"required": ["path_prefix"]},
                        ],
                    },
                )
            ],
        )
    )

    params = request.json_body["tools"][0]["parameters"]
    assert "anyOf" not in params
    assert params["description"] == "Provide at least one of: path_prefix, query."
    assert params["required"] == ["query", "path_prefix"]
    assert params["properties"]["query"]["type"] == ["string", "null"]
    assert params["properties"]["path_prefix"]["type"] == ["string", "null"]


def test_prepare_generation_request_normalizes_openai_chat_tool_schema_for_strict_mode() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_chat_completions",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-4o-mini",
            prompt="读取文稿。",
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
                            "cursors": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["paths"],
                    },
                )
            ],
        )
    )

    params = request.json_body["tools"][0]["function"]["parameters"]
    assert params["required"] == ["paths", "cursors"]
    assert params["properties"]["cursors"]["type"] == ["array", "null"]


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


def test_resolve_connection_continuation_support_uses_profile_specific_responses_strategy() -> None:
    gateway_support = resolve_connection_continuation_support("openai_responses")
    strict_support = resolve_connection_continuation_support(
        "openai_responses",
        "responses_strict",
    )

    assert gateway_support.continuation_mode == "runtime_replay"
    assert gateway_support.tolerates_interleaved_tool_results is False
    assert gateway_support.requires_full_replay_after_local_tools is True
    assert allows_provider_continuation_state(gateway_support) is False
    assert strict_support.continuation_mode == "hybrid"
    assert allows_provider_continuation_state(strict_support) is True


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
    assert request.json_body["messages"][1]["content"][0]["name"] == "project_read_documents"
    assert request.json_body["messages"][2]["content"][0]["type"] == "tool_result"
    assert "设定/人物.md" in request.json_body["messages"][2]["content"][0]["content"]


def test_prepare_generation_request_compiles_portable_tool_schema_for_anthropic() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="anthropic_messages",
                api_key="test-key",
                base_url="https://api.anthropic.com",
            ),
            model_name="claude-sonnet-4-20250514",
            prompt="检索文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            tools=[
                LLMFunctionToolDefinition(
                    name="project.search_documents",
                    description="检索项目文稿。",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "minLength": 1},
                            "path_prefix": {"type": "string", "minLength": 1},
                        },
                        "anyOf": [
                            {"required": ["query"]},
                            {"required": ["path_prefix"]},
                        ],
                    },
                )
            ],
        )
    )

    params = request.json_body["tools"][0]["input_schema"]
    assert "anyOf" not in params
    assert params["description"] == "Provide at least one of: path_prefix, query."


def test_prepare_generation_request_forces_tool_call_for_anthropic() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="anthropic_messages",
                api_key="test-key",
                base_url="https://api.anthropic.com",
            ),
            model_name="claude-sonnet-4-20250514",
            prompt="读取文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            force_tool_call=True,
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

    assert request.json_body["tool_choice"] == {
        "type": "any",
        "disable_parallel_tool_use": True,
    }


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
    assert request.json_body["messages"][2]["tool_calls"][0]["function"]["name"] == "project_read_documents"
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
        == "project_read_documents"
    )
    assert (
        request.json_body["contents"][2]["parts"][0]["functionResponse"]["name"]
        == "project_read_documents"
    )
    assert "设定/人物.md" in json.dumps(
        request.json_body["contents"][2]["parts"][0]["functionResponse"]["response"],
        ensure_ascii=False,
    )


def test_prepare_generation_request_strips_unsupported_gemini_tool_schema_keys() -> None:
    tool_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "options": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "mode": {"type": "string", "enum": ["full"]},
                },
                "required": ["mode"],
            },
        },
        "required": ["paths"],
    }
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="gemini_generate_content",
                api_key="test-key",
                base_url="https://generativelanguage.googleapis.com",
            ),
            model_name="gemini-2.5-pro",
            prompt="读一下设定。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            tools=[
                LLMFunctionToolDefinition(
                    name="project.read_documents",
                    description="读取项目文稿。",
                    parameters=tool_schema,
                )
            ],
        )
    )

    params = request.json_body["tools"][0]["functionDeclarations"][0]["parameters"]
    assert params == {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "options": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["full"]},
                },
                "required": ["mode"],
            },
        },
        "required": ["paths"],
    }
    assert tool_schema["additionalProperties"] is False
    assert tool_schema["properties"]["options"]["additionalProperties"] is False


def test_prepare_generation_request_simplifies_required_only_anyof_for_gemini() -> None:
    tool_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "path_prefix": {"type": "string", "minLength": 1},
        },
        "anyOf": [
            {"required": ["query"]},
            {"required": ["path_prefix"]},
        ],
    }
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="gemini_generate_content",
                api_key="test-key",
                base_url="https://generativelanguage.googleapis.com",
            ),
            model_name="gemini-2.5-pro",
            prompt="检索文稿。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            tools=[
                LLMFunctionToolDefinition(
                    name="project.search_documents",
                    description="检索项目文稿。",
                    parameters=tool_schema,
                )
            ],
        )
    )

    params = request.json_body["tools"][0]["functionDeclarations"][0]["parameters"]
    assert "anyOf" not in params
    assert params["description"] == "Provide at least one of: path_prefix, query."
    assert tool_schema["anyOf"] == [
        {"required": ["query"]},
        {"required": ["path_prefix"]},
    ]


def test_prepare_generation_request_forces_tool_call_for_gemini() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="gemini_generate_content",
                api_key="test-key",
                base_url="https://generativelanguage.googleapis.com",
            ),
            model_name="gemini-2.5-pro",
            prompt="读一下设定。",
            system_prompt="你是小说助手。",
            response_format="text",
            temperature=None,
            max_tokens=256,
            top_p=None,
            force_tool_call=True,
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

    assert request.json_body["toolConfig"] == {
        "functionCallingConfig": {
            "mode": "ANY",
            "allowedFunctionNames": ["project_read_documents"],
        }
    }


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


def test_prepare_generation_request_disambiguates_colliding_external_tool_names() -> None:
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_chat_completions",
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
                    parameters={"type": "object", "properties": {}, "required": []},
                ),
                LLMFunctionToolDefinition(
                    name="project_read_documents",
                    description="另一个工具。",
                    parameters={"type": "object", "properties": {}, "required": []},
                ),
            ],
        )
    )

    tool_names = [item["function"]["name"] for item in request.json_body["tools"]]
    assert tool_names[0] == "project_read_documents"
    assert tool_names[1].startswith("project_read_documents__")
    assert len(tool_names[1]) <= 64
    assert request.tool_name_aliases["project.read_documents"] == "project_read_documents"
    assert request.tool_name_aliases["project_read_documents"] == tool_names[1]


def test_parse_generation_response_decodes_external_tool_name_alias() -> None:
    normalized = parse_generation_response(
        "openai_responses",
        {
            "id": "resp_123",
            "output": [
                {
                    "id": "fc_123",
                    "type": "function_call",
                    "call_id": "call_123",
                    "name": "project_read_documents",
                    "arguments": '{"paths":["设定/人物.md"]}',
                }
            ],
        },
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert normalized.tool_calls[0].tool_name == "project.read_documents"
    assert normalized.provider_output_items[0]["payload"]["tool_name"] == "project.read_documents"


def test_parse_generation_response_preserves_openai_chat_reasoning_content_for_tool_call_items() -> None:
    normalized = parse_generation_response(
        "openai_chat_completions",
        {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": "",
                        "reasoning_content": "先分析一下再调用工具。",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "project_read_documents",
                                    "arguments": '{\"paths\":[\"设定/人物.md\"]}',
                                },
                            }
                        ],
                    },
                }
            ]
        },
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert normalized.tool_calls[0].provider_payload == {
        "reasoning_content": "先分析一下再调用工具。"
    }
    assert normalized.provider_output_items[0]["item_type"] == "tool_call"
    assert normalized.provider_output_items[0]["payload"]["provider_payload"] == {
        "reasoning_content": "先分析一下再调用工具。"
    }


def test_parse_stream_terminal_response_decodes_external_tool_name_alias() -> None:
    normalized = parse_stream_terminal_response(
        "gemini_generate_content",
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "project_read_documents",
                                    "args": {"paths": ["设定/人物.md"]},
                                }
                            }
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 4,
                "totalTokenCount": 16,
            },
        },
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert normalized.tool_calls[0].tool_name == "project.read_documents"


def test_parse_gemini_response_generates_tool_call_id_when_missing() -> None:
    normalized = parse_generation_response(
        "gemini_generate_content",
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "project.read_documents",
                                    "args": {"paths": ["设定/人物.md"]},
                                }
                            }
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 4,
                "totalTokenCount": 16,
            },
        },
    )

    assert normalized.content == ""
    assert normalized.tool_calls[0].tool_call_id == "provider:gemini_generate_content:tool_call:1"
    assert normalized.tool_calls[0].tool_name == "project.read_documents"
    assert normalized.tool_calls[0].arguments == {"paths": ["设定/人物.md"]}


def test_parse_openai_responses_response_preserves_invalid_tool_arguments_for_runtime_recovery() -> None:
    normalized = parse_generation_response(
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

    assert normalized.tool_calls[0].tool_call_id == "call_bad"
    assert normalized.tool_calls[0].tool_name == "project.read_documents"
    assert normalized.tool_calls[0].arguments == {}
    assert normalized.tool_calls[0].arguments_text == '{"paths":["设定/人物.md"]'
    assert normalized.tool_calls[0].arguments_error == "Tool call arguments JSON is invalid"
    assert normalized.provider_output_items[0]["payload"]["arguments_error"] == "Tool call arguments JSON is invalid"


def test_parse_generation_response_leaves_truncation_decision_to_callers() -> None:
    payload = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": "只返回了半截"},
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }

    normalized = parse_generation_response(
        "openai_chat_completions",
        payload,
    )

    assert normalized.content == "只返回了半截"
    assert normalized.finish_reason == "length"
    assert extract_response_truncation_reason("openai_chat_completions", payload) == "length"


def test_parse_stream_terminal_response_leaves_truncation_decision_to_callers() -> None:
    payload = {
        "id": "resp_truncated",
        "output_text": "只返回了半截",
        "incomplete_details": {"reason": "max_output_tokens"},
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
    }

    normalized = parse_stream_terminal_response(
        "openai_responses",
        payload,
    )

    assert normalized.content == "只返回了半截"
    assert normalized.finish_reason == "max_output_tokens"
    assert extract_response_truncation_reason("openai_responses", payload) == "max_output_tokens"


def test_parse_openai_responses_response_keeps_non_stream_contract_strict_for_empty_output() -> None:
    with pytest.raises(ConfigurationError, match="output must be a non-empty list"):
        parse_generation_response(
            "openai_responses",
            {
                "id": "resp_empty",
                "output": [],
            },
        )
