from __future__ import annotations

import json
from types import SimpleNamespace
import uuid

import pytest

from app.modules.workflow.service.workflow_hook_agent_runtime import (
    WorkflowHookAgentRuntime,
)
from app.modules.workflow.service.workflow_runtime_hook_support import HookExecutionContext
from app.shared.runtime.template_renderer import SkillTemplateRenderer


def _build_context(*, agents_snapshot: dict, skills_snapshot: dict) -> HookExecutionContext:
    workflow = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        agents_snapshot=agents_snapshot,
        skills_snapshot=skills_snapshot,
    )
    workflow_config = SimpleNamespace(id="workflow.test")
    node = SimpleNamespace(id="chapter_gen", name="章节生成", node_type="generate")
    return HookExecutionContext(
        db=None,
        workflow=workflow,
        workflow_config=workflow_config,
        node=node,
        event="after_generate",
        owner_id=uuid.uuid4(),
        payload={
            "chapter": {"number": 1},
            "content": {"text": "第一章正文"},
        },
        node_execution_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_workflow_hook_agent_runtime_runs_text_agent_chain() -> None:
    call_log: list[object] = []
    context = _build_context(
        agents_snapshot={
            "agent.hook_summary": {
                "id": "agent.hook_summary",
                "name": "Hook Summary Agent",
                "type": "checker",
                "system_prompt": "你是工作流 hook 摘要助手。",
                "skills": ["skill.hook.summary"],
                "model": {"provider": "openai", "name": "gpt-4o"},
            }
        },
        skills_snapshot={
            "skill.hook.summary": {
                "id": "skill.hook.summary",
                "name": "Hook Summary Skill",
                "category": "utility",
                "prompt": "请总结第{{ chapter_number }}章：{{ content }}",
            }
        },
    )

    async def llm_caller(db, workflow, workflow_config, prompt_bundle, **kwargs):
        del db, workflow, workflow_config
        call_log.append((prompt_bundle, kwargs))
        return {"content": "第1章摘要：主角踏上逃亡之路。"}

    runtime = WorkflowHookAgentRuntime(
        template_renderer=SkillTemplateRenderer(),
        llm_caller=llm_caller,
        parse_json=lambda value: (_ for _ in ()).throw(AssertionError("should not parse json")),
    )

    result = await runtime.run(
        context,
        agent_id="agent.hook_summary",
        input_mapping={
            "chapter_number": "chapter.number",
            "content": "content.text",
        },
    )

    assert result == "第1章摘要：主角踏上逃亡之路。"
    assert len(call_log) == 1
    prompt_bundle, kwargs = call_log[0]
    assert "请总结第1章：第一章正文" in prompt_bundle["prompt"]
    assert prompt_bundle["response_format"] == "text"
    assert kwargs["usage_type"] == "analysis"
    assert kwargs["node_execution_id"] == context.node_execution_id


@pytest.mark.asyncio
async def test_workflow_hook_agent_runtime_runs_json_agent_chain() -> None:
    context = _build_context(
        agents_snapshot={
            "agent.reviewer": {
                "id": "agent.reviewer",
                "name": "Reviewer Agent",
                "type": "reviewer",
                "system_prompt": "你是审核助手。",
                "skills": ["skill.hook.review"],
                "model": {"provider": "openai", "name": "gpt-4o"},
            }
        },
        skills_snapshot={
            "skill.hook.review": {
                "id": "skill.hook.review",
                "name": "Hook Review Skill",
                "category": "utility",
                "prompt": "请审核：{{ payload_json }}",
            }
        },
    )

    runtime = WorkflowHookAgentRuntime(
        template_renderer=SkillTemplateRenderer(),
        llm_caller=lambda db, workflow, workflow_config, prompt_bundle, **kwargs: _return_async(
            {"content": '{"score": 1, "summary": "ok"}'}
        ),
        parse_json=json.loads,
    )

    result = await runtime.run(
        context,
        agent_id="agent.reviewer",
        input_mapping={},
    )

    assert result == {"score": 1, "summary": "ok"}


@pytest.mark.asyncio
async def test_workflow_hook_agent_runtime_requires_agent_model_configuration() -> None:
    context = _build_context(
        agents_snapshot={
            "agent.invalid": {
                "id": "agent.invalid",
                "name": "Invalid Agent",
                "type": "checker",
                "system_prompt": "你是工作流 hook 助手。",
                "skills": ["skill.hook.summary"],
            }
        },
        skills_snapshot={
            "skill.hook.summary": {
                "id": "skill.hook.summary",
                "name": "Hook Summary Skill",
                "category": "utility",
                "prompt": "请总结：{{ payload_json }}",
            }
        },
    )

    runtime = WorkflowHookAgentRuntime(
        template_renderer=SkillTemplateRenderer(),
        llm_caller=lambda db, workflow, workflow_config, prompt_bundle, **kwargs: _return_async(
            {"content": "unused"}
        ),
        parse_json=json.loads,
    )

    with pytest.raises(Exception, match="missing model configuration"):
        await runtime.run(
            context,
            agent_id="agent.invalid",
            input_mapping={},
        )


async def _return_async(value):
    return value
