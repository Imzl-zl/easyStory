from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.service import create_config_registry_query_service

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


async def test_config_registry_query_service_lists_repository_configs() -> None:
    service = create_config_registry_query_service(config_loader=ConfigLoader(CONFIG_ROOT))

    skills = await service.list_skills()
    agents = await service.list_agents()
    hooks = await service.list_hooks()
    workflows = await service.list_workflows()

    skill = _get_by_id(skills, "skill.chapter.xuanhuan")
    assert skill.category == "chapter"
    assert skill.input_keys[:4] == [
        "project_setting",
        "outline",
        "opening_plan",
        "chapter_task",
    ]
    assert skill.model is not None
    assert skill.model.provider == "anthropic"
    assert skill.model.name == "claude-sonnet-4-20250514"

    agent = _get_by_id(agents, "agent.style_checker")
    assert agent.agent_type == "reviewer"
    assert agent.skill_ids == ["skill.review.style"]
    assert agent.output_schema_keys == []
    assert agent.model is not None
    assert agent.model.required_capabilities == ["json_schema_output"]

    hook = _get_by_id(hooks, "hook.auto_save")
    assert hook.trigger_event == "after_generate"
    assert hook.trigger_node_types == ["generate"]
    assert hook.action_type == "script"
    assert hook.retry_enabled is False

    workflow = _get_by_id(workflows, "workflow.xuanhuan_manual")
    assert workflow.mode == "manual"
    assert workflow.default_fix_skill == "skill.fix.xuanhuan"
    assert workflow.default_inject_types == ["project_setting", "outline"]
    assert workflow.node_count == 5
    chapter_node = _get_by_id(workflow.nodes, "chapter_gen")
    assert chapter_node.loop_enabled is True
    assert chapter_node.hook_ids == ["hook.auto_save"]
    assert chapter_node.reviewer_ids == ["agent.style_checker"]
    export_node = _get_by_id(workflow.nodes, "export")
    assert export_node.formats == ["txt", "markdown"]


async def test_config_registry_query_service_reads_agent_detail() -> None:
    service = create_config_registry_query_service(config_loader=ConfigLoader(CONFIG_ROOT))

    agent = await service.get_agent("agent.style_checker")

    assert agent.agent_type == "reviewer"
    assert agent.skill_ids == ["skill.review.style"]
    assert agent.system_prompt.startswith("你是一位专业的小说文风审核专家")
    assert agent.output_schema is None


def _get_by_id(items, config_id: str):
    for item in items:
        if item.id == config_id:
            return item
    raise AssertionError(f"Config item not found: {config_id}")
