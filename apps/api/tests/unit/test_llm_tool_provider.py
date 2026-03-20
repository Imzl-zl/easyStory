from __future__ import annotations

import asyncio

from app.shared.runtime.llm_tool_provider import LLMToolProvider


def test_execute_passes_provider_to_completion_payload() -> None:
    captured: dict = {}

    async def completion_callable(**kwargs):
        captured.update(kwargs)
        return {
            "choices": [{"message": {"content": "生成结果"}}],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 34,
                "total_tokens": 46,
            },
        }

    provider = LLMToolProvider(completion_callable=completion_callable)

    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "openai", "name": "gpt-4o-mini"},
                "credential": {"api_key": "test-key"},
            },
        )
    )

    assert captured["model"] == "gpt-4o-mini"
    assert captured["custom_llm_provider"] == "openai"
    assert result["provider"] == "openai"
    assert result["content"] == "生成结果"
