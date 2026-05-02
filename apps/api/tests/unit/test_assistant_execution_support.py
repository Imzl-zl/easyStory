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
from app.modules.assistant.service.context.assistant_prompt_render_support import (
    render_message_only_prompt,
    render_skill_prompt,
)
from app.modules.assistant.service.context.assistant_prompt_support import (
    build_document_context_injection_snapshot,
    build_project_tool_guidance_snapshot,
    build_project_tool_guidance_snapshot_from_discovery_decision,
    resolve_project_tool_discovery_decision,
)
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


def test_assistant_turn_request_accepts_long_history_snapshot() -> None:
    messages = [
        AssistantMessageDTO(
            role="assistant" if index % 2 else "user",
            content=f"消息 {index}",
        )
        for index in range(1, 28)
    ]
    messages.append(AssistantMessageDTO(role="user", content="继续写。"))

    payload = AssistantTurnRequestDTO(
        conversation_id="conversation-long-history-test",
        client_turn_id="turn-long-history-test-1",
        messages=messages,
        requested_write_scope="disabled",
    )

    assert len(payload.messages) == len(messages)


def test_render_message_only_prompt_includes_project_search_documents_guidance() -> None:
    project_tool_guidance = build_project_tool_guidance_snapshot(
        has_project_scope=True,
        latest_user_message="帮我检查这一卷的人物关系和时间线是否一致。",
        document_context=None,
    )

    prompt = render_message_only_prompt(
        [AssistantMessageDTO(role="user", content="帮我检查这一卷的人物关系和时间线是否一致。")],
        tool_guidance_snapshot=project_tool_guidance.model_dump(mode="json"),
    )

    assert "project.search_documents" in prompt
    assert "project.read_documents" in prompt
    assert "人物关系、势力关系、时间轴、事件或伏笔回收" in prompt
    assert prompt.endswith("帮我检查这一卷的人物关系和时间线是否一致。")


def test_render_skill_prompt_messages_json_path_keeps_project_search_documents_guidance() -> None:
    project_tool_guidance = build_project_tool_guidance_snapshot(
        has_project_scope=True,
        latest_user_message="检查全书连续性。",
        document_context=None,
    )

    prompt = render_skill_prompt(
        rendered_skill_prompt="请根据 messages_json 总结 continuity 风险。",
        messages=[AssistantMessageDTO(role="user", content="检查全书连续性。")],
        referenced_variables={"messages_json"},
        tool_guidance_snapshot=project_tool_guidance.model_dump(mode="json"),
    )

    assert "project.search_documents" in prompt
    assert "project.read_documents" in prompt


def test_render_message_only_prompt_prefers_document_context_over_project_search_guidance() -> None:
    project_tool_guidance = build_project_tool_guidance_snapshot(
        has_project_scope=True,
        latest_user_message="基于当前文稿继续写。",
        document_context={
            "active_path": "正文/第001章.md",
            "selected_paths": ["设定/人物.md"],
        },
    )
    assert project_tool_guidance is None

    prompt = render_message_only_prompt(
        [AssistantMessageDTO(role="user", content="基于当前文稿继续写。")],
        document_context_injection_snapshot=build_document_context_injection_snapshot(
            {
                "active_path": "正文/第001章.md",
                "selected_paths": ["设定/人物.md"],
            }
        ),
    )

    assert "【当前文稿上下文】" in prompt
    assert "project.read_documents" in prompt
    assert "project.search_documents" not in prompt


def test_render_message_only_prompt_omits_project_search_documents_guidance_without_project_scope() -> None:
    prompt = render_message_only_prompt(
        [AssistantMessageDTO(role="user", content="简单聊聊这一章。")]
    )

    assert "project.search_documents" not in prompt
    assert "项目范围工具提示" not in prompt


def test_render_message_only_prompt_omits_project_search_documents_guidance_for_non_continuity_question() -> None:
    prompt = render_message_only_prompt(
        [AssistantMessageDTO(role="user", content="先读一下人物设定，再给我一个悬疑开场方向。")]
    )

    assert "project.search_documents" not in prompt
    assert prompt == "【用户当前消息】\n先读一下人物设定，再给我一个悬疑开场方向。"


def test_resolve_project_tool_discovery_decision_requires_visible_tools() -> None:
    decision = resolve_project_tool_discovery_decision(
        has_project_scope=True,
        visible_tool_names=("project.search_documents",),
        latest_user_message="帮我检查这一卷的人物关系和时间线是否一致。",
        document_context=None,
    )

    assert decision is None


def test_build_project_tool_guidance_snapshot_projects_resolved_discovery_decision() -> None:
    decision = resolve_project_tool_discovery_decision(
        has_project_scope=True,
        visible_tool_names=("project.search_documents", "project.read_documents"),
        latest_user_message="帮我检查这一卷的人物关系和时间线是否一致。",
        document_context=None,
    )

    guidance = build_project_tool_guidance_snapshot_from_discovery_decision(decision)

    assert decision is not None
    assert guidance is not None
    assert guidance.guidance_type == decision.decision_type
    assert guidance.tool_names == decision.tool_names
    assert guidance.trigger_keywords == decision.trigger_keywords
    assert guidance.discovery_source == decision.discovery_source
    assert "完整文稿全文" in guidance.content
    assert "patch" in guidance.content


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
