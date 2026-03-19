import re
from pathlib import Path

import pytest

from app.modules.config_registry.infrastructure.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.modules.config_registry.schemas.config_schemas import HookConfig, SkillConfig


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


def _build_loader() -> ConfigLoader:
    return ConfigLoader(CONFIG_ROOT)


def _build_strict_skill() -> SkillConfig:
    return SkillConfig.model_validate(
        {
            "id": "skill.strict",
            "name": "Strict Skill",
            "category": "outline",
            "prompt": "x",
            "inputs": {
                "genre": {"type": "string", "required": True, "enum": ["玄幻", "科幻"]},
                "target_chapters": {
                    "type": "integer",
                    "required": True,
                    "min": 10,
                    "max": 100,
                },
                "chapter_list": {
                    "type": "array",
                    "required": True,
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {"type": "integer", "required": True},
                            "title": {"type": "string", "required": True, "min_length": 2},
                        },
                    },
                },
                "settings": {
                    "type": "object",
                    "required": True,
                    "properties": {
                        "tone": {"type": "string", "required": True, "enum": ["热血", "克制"]}
                    },
                },
            },
        }
    )


def _build_valid_input() -> dict:
    return {
        "genre": "玄幻",
        "target_chapters": 50,
        "chapter_list": [{"number": 1, "title": "开篇"}],
        "settings": {"tone": "热血"},
    }


def test_hook_action_validates_type_specific_config() -> None:
    hook = HookConfig.model_validate(
        {
            "id": "hook.agent_call",
            "name": "Agent Call",
            "trigger": {"event": "after_generate"},
            "action": {"type": "agent", "config": {"agent_id": "agent.style_checker"}},
        }
    )

    assert hook.action.config == {
        "agent_id": "agent.style_checker",
        "input_mapping": {},
    }


@pytest.mark.parametrize(
    ("action_type", "config", "field_name"),
    [
        ("script", {"module": "app.hooks.builtin"}, "function"),
        ("webhook", {"method": "POST"}, "url"),
        ("agent", {}, "agent_id"),
    ],
)
def test_hook_action_rejects_missing_required_config(action_type, config, field_name) -> None:
    with pytest.raises(ValueError, match=field_name):
        HookConfig.model_validate(
            {
                "id": "hook.invalid",
                "name": "Invalid Hook",
                "trigger": {"event": "after_generate"},
                "action": {"type": action_type, "config": config},
            }
        )


def test_validate_skill_input_enforces_recursive_schema_rules() -> None:
    assert _build_loader().validate_skill_input(_build_strict_skill(), _build_valid_input())


@pytest.mark.parametrize(
    ("input_data", "error_fragment"),
    [
        (
            {
                "genre": "都市",
                "target_chapters": 50,
                "chapter_list": [{"number": 1, "title": "开篇"}],
                "settings": {"tone": "热血"},
            },
            "genre",
        ),
        (
            {
                "genre": "玄幻",
                "target_chapters": 5,
                "chapter_list": [{"number": 1, "title": "开篇"}],
                "settings": {"tone": "热血"},
            },
            "target_chapters",
        ),
        (
            {
                "genre": "玄幻",
                "target_chapters": 50,
                "chapter_list": [{"number": 1, "title": "A"}],
                "settings": {"tone": "热血"},
            },
            "chapter_list[0].title",
        ),
        (
            {
                "genre": "玄幻",
                "target_chapters": 50,
                "chapter_list": [{"number": "1", "title": "开篇"}],
                "settings": {"tone": "热血"},
            },
            "chapter_list[0].number",
        ),
        (
            {
                "genre": "玄幻",
                "target_chapters": 50,
                "chapter_list": [{"number": 1, "title": "开篇"}],
                "settings": {},
            },
            "settings.tone",
        ),
        (
            {
                "genre": "玄幻",
                "target_chapters": 50,
                "chapter_list": [{"number": 1, "title": "开篇"}],
                "settings": {"tone": "热血", "extra": "x"},
            },
            "settings.extra",
        ),
    ],
)
def test_validate_skill_input_rejects_invalid_nested_values(input_data, error_fragment) -> None:
    with pytest.raises(ConfigurationError, match=re.escape(error_fragment)):
        _build_loader().validate_skill_input(_build_strict_skill(), input_data)


def test_repository_chapter_skill_uses_previous_content_variable() -> None:
    skill = _build_loader().load_skill("skill.chapter.xuanhuan")

    assert "{{ previous_content }}" in skill.prompt
    assert "previous_content" in skill.variables
    assert "previous_chapters" not in skill.variables
