import re
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.config_registry.infrastructure.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.modules.config_registry.schemas.config_schemas import (
    ContextInjectionItem,
    HookConfig,
    ModelConfig,
    SkillConfig,
)


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
        (
            {
                "genre": "玄幻",
                "target_chapters": 50,
                "chapter_list": [{"number": 1, "title": "开篇"}],
                "settings": {"tone": "热血"},
                "extra": "x",
            },
            "Unknown field: extra",
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


def test_context_injection_item_rejects_unsupported_type() -> None:
    with pytest.raises(ValidationError, match="Input should be"):
        ContextInjectionItem.model_validate({"type": "chapter_list"})


@pytest.mark.parametrize("inject_type", ["chapter_summary", "world_setting", "character_profile"])
def test_context_injection_item_accepts_supported_projection_types(inject_type: str) -> None:
    payload = {"type": inject_type}
    if inject_type == "chapter_summary":
        payload["count"] = 3

    item = ContextInjectionItem.model_validate(payload)

    assert item.inject_type == inject_type


def test_context_injection_item_accepts_style_reference() -> None:
    analysis_id = uuid.uuid4()

    item = ContextInjectionItem.model_validate(
        {
            "type": "style_reference",
            "analysis_id": str(analysis_id),
            "inject_fields": [" writing_style ", "narrative_perspective"],
        }
    )

    assert item.inject_type == "style_reference"
    assert item.analysis_id == analysis_id
    assert item.inject_fields == ["writing_style", "narrative_perspective"]


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "style_reference", "inject_fields": ["writing_style"]},
        {"type": "style_reference", "analysis_id": str(uuid.uuid4())},
        {
            "type": "outline",
            "analysis_id": str(uuid.uuid4()),
            "inject_fields": ["writing_style"],
        },
    ],
)
def test_context_injection_item_validates_style_reference_shape(payload) -> None:
    with pytest.raises(ValidationError):
        ContextInjectionItem.model_validate(payload)


def test_model_config_allows_openai_reasoning_without_model_specific_matrix() -> None:
    model = ModelConfig.model_validate(
        {
            "provider": "openai",
            "name": "gpt-5.1",
            "reasoning_effort": "minimal",
        }
    )

    assert model.reasoning_effort == "minimal"


def test_model_config_rejects_openai_family_thinking_fields() -> None:
    with pytest.raises(
        ValidationError,
        match="thinking_level and thinking_budget are only valid for Gemini native requests",
    ):
        ModelConfig.model_validate(
            {
                "provider": "openai",
                "name": "gpt-4.1",
                "thinking_level": "low",
            }
        )


def test_model_config_rejects_cross_vendor_reasoning_fields() -> None:
    with pytest.raises(
        ValidationError,
        match="reasoning_effort cannot be combined with thinking_level or thinking_budget",
    ):
        ModelConfig.model_validate(
            {
                "provider": "openai",
                "name": "gpt-5.4",
                "reasoning_effort": "high",
                "thinking_budget": 0,
            }
        )
