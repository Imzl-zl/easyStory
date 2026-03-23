from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.service import (
    AgentConfigUpdateDTO,
    create_config_registry_agent_write_service,
    create_config_registry_query_service,
)
from app.shared.runtime.errors import BusinessRuleError

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"
TARGET_AGENT_ID = "agent.style_checker"


async def test_config_registry_agent_write_service_reads_and_updates_agent(tmp_path) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_agent_write_service(config_loader=loader)

    detail = await query_service.get_agent(TARGET_AGENT_ID)

    assert detail.agent_type == "reviewer"
    assert detail.skill_ids == ["skill.review.style"]

    payload = AgentConfigUpdateDTO(
        **{
            **detail.model_dump(),
            "name": "文风检查员-已更新",
            "system_prompt": "你是一位严格的文风审核专家。\n\n请输出 ReviewResult JSON。",
            "mcp_servers": ["ctx.story_bible"],
        }
    )

    updated = await write_service.update_agent(TARGET_AGENT_ID, payload)

    assert updated.name == "文风检查员-已更新"
    assert updated.mcp_servers == ["ctx.story_bible"]
    assert updated.system_prompt.endswith("ReviewResult JSON。")

    reloaded = await query_service.get_agent(TARGET_AGENT_ID)
    assert reloaded.name == "文风检查员-已更新"
    source_text = loader.get_source_path(TARGET_AGENT_ID).read_text(encoding="utf-8")
    assert "name: 文风检查员-已更新" in source_text
    assert "system_prompt: |" in source_text


async def test_config_registry_agent_write_service_rejects_invalid_skill_without_touching_file(
    tmp_path,
) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_agent_write_service(config_loader=loader)
    source_path = loader.get_source_path(TARGET_AGENT_ID)
    original_text = source_path.read_text(encoding="utf-8")
    detail = await query_service.get_agent(TARGET_AGENT_ID)

    payload = AgentConfigUpdateDTO(
        **{
            **detail.model_dump(),
            "skill_ids": ["skill.missing"],
        }
    )

    with pytest.raises(BusinessRuleError, match="skill.missing"):
        await write_service.update_agent(TARGET_AGENT_ID, payload)

    assert source_path.read_text(encoding="utf-8") == original_text


def _copy_config_root(tmp_path: Path) -> Path:
    temp_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, temp_root)
    return temp_root
