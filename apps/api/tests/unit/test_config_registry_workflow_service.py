from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.service import (
    WorkflowConfigUpdateDTO,
    create_config_registry_query_service,
    create_config_registry_workflow_write_service,
)
from app.shared.runtime.errors import BusinessRuleError

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"
TARGET_WORKFLOW_ID = "workflow.xuanhuan_manual"


async def test_config_registry_workflow_write_service_reads_and_updates_workflow(
    tmp_path,
) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_workflow_write_service(config_loader=loader)

    detail = await query_service.get_workflow(TARGET_WORKFLOW_ID)

    assert detail.context_injection is not None
    assert detail.context_injection.default_inject[0].inject_type == "project_setting"

    document = detail.model_dump()
    document["name"] = "玄幻小说手动创作-已更新"
    document["settings"]["save_on_step"] = False
    _get_by_id(document["nodes"], "chapter_gen")["context_injection"] = [
        {
            "inject_type": "chapter_task",
            "required": True,
            "count": None,
            "analysis_id": None,
            "inject_fields": [],
        }
    ]
    _get_by_id(document["nodes"], "export")["formats"] = ["txt", "markdown", "docx"]
    payload = WorkflowConfigUpdateDTO(**document)

    updated = await write_service.update_workflow(TARGET_WORKFLOW_ID, payload)

    assert updated.name == "玄幻小说手动创作-已更新"
    assert updated.settings.save_on_step is False
    chapter_node = _get_by_id(updated.nodes, "chapter_gen")
    assert chapter_node.context_injection[0].inject_type == "chapter_task"
    export_node = _get_by_id(updated.nodes, "export")
    assert export_node.formats == ["txt", "markdown", "docx"]

    reloaded = await query_service.get_workflow(TARGET_WORKFLOW_ID)
    assert reloaded.name == "玄幻小说手动创作-已更新"
    source_text = loader.get_source_path(TARGET_WORKFLOW_ID).read_text(encoding="utf-8")
    assert "name: 玄幻小说手动创作-已更新" in source_text
    assert "type: chapter_task" in source_text
    assert "docx" in source_text


async def test_config_registry_workflow_write_service_rejects_missing_agent_without_touching_file(
    tmp_path,
) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_workflow_write_service(config_loader=loader)
    source_path = loader.get_source_path(TARGET_WORKFLOW_ID)
    original_text = source_path.read_text(encoding="utf-8")
    detail = await query_service.get_workflow(TARGET_WORKFLOW_ID)
    document = detail.model_dump()
    _get_by_id(document["nodes"], "chapter_gen")["reviewer_ids"] = ["agent.missing"]
    payload = WorkflowConfigUpdateDTO(**document)

    with pytest.raises(BusinessRuleError, match="agent.missing"):
        await write_service.update_workflow(TARGET_WORKFLOW_ID, payload)

    assert source_path.read_text(encoding="utf-8") == original_text


async def test_config_registry_workflow_write_service_rejects_generate_node_without_skill(
    tmp_path,
) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_workflow_write_service(config_loader=loader)
    source_path = loader.get_source_path(TARGET_WORKFLOW_ID)
    original_text = source_path.read_text(encoding="utf-8")
    detail = await query_service.get_workflow(TARGET_WORKFLOW_ID)
    document = detail.model_dump()
    _get_by_id(document["nodes"], "chapter_gen")["skill_id"] = None
    payload = WorkflowConfigUpdateDTO(**document)

    with pytest.raises(BusinessRuleError, match="generate node requires skill"):
        await write_service.update_workflow(TARGET_WORKFLOW_ID, payload)

    assert source_path.read_text(encoding="utf-8") == original_text


def _get_by_id(items, workflow_id: str):
    for item in items:
        item_id = item["id"] if isinstance(item, dict) else item.id
        if item_id == workflow_id:
            return item
    raise AssertionError(f"Workflow item not found: {workflow_id}")


def _copy_config_root(tmp_path: Path) -> Path:
    temp_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, temp_root)
    return temp_root
