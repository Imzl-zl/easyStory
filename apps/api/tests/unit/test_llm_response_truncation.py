from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol import HttpJsonResponse
from app.shared.runtime.llm.llm_tool_provider import LLMToolProvider


@pytest.mark.parametrize(
    ("api_dialect", "response_body"),
    [
        (
            "openai_chat_completions",
            {
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
            },
        ),
        (
            "openai_responses",
            {
                "output_text": "只返回了半截",
                "incomplete_details": {"reason": "max_output_tokens"},
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            },
        ),
        (
            "anthropic_messages",
            {
                "content": [{"type": "text", "text": "只返回了半截"}],
                "stop_reason": "max_tokens",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
        ),
        (
            "gemini_generate_content",
            {
                "candidates": [
                    {
                        "finishReason": "MAX_TOKENS",
                        "content": {"parts": [{"text": "只返回了半截"}]},
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 20,
                    "totalTokenCount": 30,
                },
            },
        ),
    ],
)
def test_execute_rejects_truncated_non_stream_responses(
    api_dialect: str,
    response_body: dict[str, object],
) -> None:
    async def request_sender(_request):
        return HttpJsonResponse(
            status_code=200,
            json_body=response_body,
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)

    with pytest.raises(
        ConfigurationError,
        match="上游在输出尚未完成时提前停止了这次回复",
    ):
        asyncio.run(
            provider.execute(
                "llm.generate",
                {
                    "prompt": "请继续展开",
                    "model": {"provider": "test-provider", "name": "test-model"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": api_dialect,
                    },
                },
            )
        )


def test_execute_allows_truncated_json_object_when_content_is_complete() -> None:
    async def request_sender(_request):
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "candidates": [
                    {
                        "finishReason": "MAX_TOKENS",
                        "content": {
                            "parts": [
                                {
                                    "text": '{"genre":"玄幻","core_conflict":"主角在宗门压制中夺回成长机会"}'
                                }
                            ]
                        },
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 20,
                    "totalTokenCount": 30,
                },
            },
            text="",
        )

    provider = LLMToolProvider(request_sender=request_sender)

    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "提取项目设定",
                "response_format": "json_object",
                "model": {"provider": "gemini", "name": "gemini-2.5-pro"},
                "credential": {
                    "api_key": "test-key",
                    "api_dialect": "gemini_generate_content",
                },
            },
        )
    )

    assert result["content"] == (
        '{"genre":"玄幻","core_conflict":"主角在宗门压制中夺回成长机会"}'
    )
