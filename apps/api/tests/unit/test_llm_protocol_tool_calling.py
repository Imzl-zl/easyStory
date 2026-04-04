from __future__ import annotations

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm_protocol_requests import prepare_generation_request
from app.shared.runtime.llm_protocol_responses import parse_generation_response
from app.shared.runtime.llm_protocol_types import (
    LLMConnection,
    LLMFunctionToolDefinition,
    LLMGenerateRequest,
)


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
    assert request.json_body["parallel_tool_calls"] is False


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
