from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.assistant.service.dto import (
    AssistantContinuationAnchorDTO,
    AssistantDocumentContextDTO,
    AssistantMessageDTO,
    AssistantTurnRequestDTO,
    build_turn_messages_digest,
)
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


def test_assistant_turn_request_rejects_continuation_anchor_digest_mismatch() -> None:
    with pytest.raises(ValidationError, match="conversation_state_mismatch"):
        AssistantTurnRequestDTO(
            conversation_id="conversation-continuation-test",
            client_turn_id="turn-continuation-test-1",
            continuation_anchor=AssistantContinuationAnchorDTO(
                previous_run_id="c504ffcb-09f5-4552-af95-149a951d95db",
                messages_digest="wrong-digest",
            ),
            messages=[
                AssistantMessageDTO(role="assistant", content="上一轮我已经给过方向。"),
                AssistantMessageDTO(role="user", content="这一轮继续往下写。"),
            ],
            requested_write_scope="disabled",
        )


def test_assistant_turn_request_rejects_non_active_write_target_scope() -> None:
    parent_messages = [AssistantMessageDTO(role="assistant", content="先看一下设定。")]

    with pytest.raises(ValidationError, match="unsupported_write_target_scope"):
        AssistantTurnRequestDTO(
            conversation_id="conversation-write-scope-test",
            client_turn_id="turn-write-scope-test-1",
            continuation_anchor=AssistantContinuationAnchorDTO(
                previous_run_id="4fae7626-f758-4dcb-a0e4-f529dfba767f",
                messages_digest=build_turn_messages_digest(parent_messages),
            ),
            document_context=AssistantDocumentContextDTO(active_document_ref="doc.active"),
            messages=[
                *parent_messages,
                AssistantMessageDTO(role="user", content="帮我直接改另一个文稿。"),
            ],
            requested_write_scope="turn",
            requested_write_targets=["doc.other"],
        )


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
