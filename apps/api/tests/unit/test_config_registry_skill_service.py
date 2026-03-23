from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.service import (
    SkillConfigUpdateDTO,
    create_config_registry_query_service,
    create_config_registry_skill_write_service,
)
from app.shared.runtime.errors import BusinessRuleError

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"
TARGET_SKILL_ID = "skill.review.style"


async def test_config_registry_skill_write_service_reads_and_updates_skill(tmp_path) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_skill_write_service(config_loader=loader)

    detail = await query_service.get_skill(TARGET_SKILL_ID)

    assert detail.name == "文风审核"
    assert detail.variables["content"].field_type == "string"

    payload = SkillConfigUpdateDTO(
        **{
            **detail.model_dump(by_alias=True),
            "name": "文风审核-已更新",
            "prompt": "你是一名文风编辑。\n\n请检查内容：\n{{ content }}",
            "tags": ["审核", "文风", "已更新"],
        }
    )

    updated = await write_service.update_skill(TARGET_SKILL_ID, payload)

    assert updated.name == "文风审核-已更新"
    assert updated.tags == ["审核", "文风", "已更新"]
    assert updated.prompt.endswith("{{ content }}")

    reloaded = await query_service.get_skill(TARGET_SKILL_ID)
    assert reloaded.name == "文风审核-已更新"
    source_text = loader.get_source_path(TARGET_SKILL_ID).read_text(encoding="utf-8")
    assert "name: 文风审核-已更新" in source_text
    assert "prompt: |" in source_text


async def test_config_registry_skill_write_service_rejects_invalid_prompt_without_touching_file(
    tmp_path,
) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_skill_write_service(config_loader=loader)
    source_path = loader.get_source_path(TARGET_SKILL_ID)
    original_text = source_path.read_text(encoding="utf-8")
    detail = await query_service.get_skill(TARGET_SKILL_ID)

    payload = SkillConfigUpdateDTO(
        **{
            **detail.model_dump(by_alias=True),
            "prompt": "{{ content }} {{ missing_input }}",
        }
    )

    with pytest.raises(BusinessRuleError, match="Undeclared variable: missing_input"):
        await write_service.update_skill(TARGET_SKILL_ID, payload)

    assert source_path.read_text(encoding="utf-8") == original_text


def _copy_config_root(tmp_path: Path) -> Path:
    temp_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, temp_root)
    return temp_root
