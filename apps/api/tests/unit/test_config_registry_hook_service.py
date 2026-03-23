from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.service import (
    HookConfigUpdateDTO,
    create_config_registry_hook_write_service,
    create_config_registry_query_service,
)
from app.shared.runtime.errors import BusinessRuleError

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"
TARGET_HOOK_ID = "hook.auto_save"


async def test_config_registry_hook_write_service_reads_and_updates_hook(tmp_path) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_hook_write_service(config_loader=loader)

    detail = await query_service.get_hook(TARGET_HOOK_ID)

    assert detail.action.action_type == "script"
    assert detail.trigger.event == "after_generate"

    payload = HookConfigUpdateDTO(
        **{
            **detail.model_dump(),
            "name": "自动保存-已更新",
            "priority": 5,
            "action": {
                "action_type": "script",
                "config": {
                    "module": "app.hooks.builtin",
                    "function": "auto_save_content",
                    "params": {"save_version": True, "save_snapshot": True},
                },
            },
        }
    )

    updated = await write_service.update_hook(TARGET_HOOK_ID, payload)

    assert updated.name == "自动保存-已更新"
    assert updated.priority == 5
    assert updated.action.config["params"]["save_snapshot"] is True

    reloaded = await query_service.get_hook(TARGET_HOOK_ID)
    assert reloaded.name == "自动保存-已更新"
    source_text = loader.get_source_path(TARGET_HOOK_ID).read_text(encoding="utf-8")
    assert "name: 自动保存-已更新" in source_text
    assert "save_snapshot: true" in source_text


async def test_config_registry_hook_write_service_rejects_missing_agent_without_touching_file(
    tmp_path,
) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_hook_write_service(config_loader=loader)
    source_path = loader.get_source_path(TARGET_HOOK_ID)
    original_text = source_path.read_text(encoding="utf-8")
    detail = await query_service.get_hook(TARGET_HOOK_ID)

    payload = HookConfigUpdateDTO(
        **{
            **detail.model_dump(),
            "action": {
                "action_type": "agent",
                "config": {"agent_id": "agent.missing"},
            },
        }
    )

    with pytest.raises(BusinessRuleError, match="agent.missing"):
        await write_service.update_hook(TARGET_HOOK_ID, payload)

    assert source_path.read_text(encoding="utf-8") == original_text


async def test_config_registry_hook_write_service_rejects_invalid_action_config(
    tmp_path,
) -> None:
    temp_root = _copy_config_root(tmp_path)
    loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=loader)
    write_service = create_config_registry_hook_write_service(config_loader=loader)
    source_path = loader.get_source_path(TARGET_HOOK_ID)
    original_text = source_path.read_text(encoding="utf-8")
    detail = await query_service.get_hook(TARGET_HOOK_ID)

    payload = HookConfigUpdateDTO(
        **{
            **detail.model_dump(),
            "action": {
                "action_type": "script",
                "config": {
                    "module": "app.hooks.builtin",
                    "unexpected": True,
                },
            },
        }
    )

    with pytest.raises(BusinessRuleError, match="action.function"):
        await write_service.update_hook(TARGET_HOOK_ID, payload)

    assert source_path.read_text(encoding="utf-8") == original_text


def _copy_config_root(tmp_path: Path) -> Path:
    temp_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, temp_root)
    return temp_root
