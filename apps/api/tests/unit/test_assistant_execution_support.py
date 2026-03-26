from __future__ import annotations

import pytest

from app.modules.assistant.service.assistant_execution_support import resolve_hook_agent_output
from app.modules.config_registry.schemas import AgentConfig
from app.shared.runtime.errors import ConfigurationError


def test_resolve_hook_agent_output_parses_json_string() -> None:
    agent = _build_structured_agent()

    result = resolve_hook_agent_output(
        agent,
        '{"summary":"今天的新闻聚焦科技与国际局势。","sentiment":"neutral"}',
    )

    assert result == {
        "summary": "今天的新闻聚焦科技与国际局势。",
        "sentiment": "neutral",
    }


def test_resolve_hook_agent_output_rejects_invalid_json_string() -> None:
    agent = _build_structured_agent()

    with pytest.raises(ConfigurationError, match="valid JSON"):
        resolve_hook_agent_output(agent, "{not-json}")


def _build_structured_agent() -> AgentConfig:
    return AgentConfig.model_validate(
        {
            "id": "agent.hook_structured_summary",
            "name": "结构化 Hook 摘要助手",
            "type": "checker",
            "system_prompt": "你负责把回复整理成结构化摘要。",
            "skills": ["skill.assistant.hook_structured_summary"],
            "output_schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "sentiment": {"type": "string"},
                },
            },
            "model": {"provider": "openai", "name": "gpt-4o-mini"},
        }
    )
