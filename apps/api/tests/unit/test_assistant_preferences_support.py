from __future__ import annotations

import pytest

from app.modules.assistant.service.preferences.preferences_support import (
    apply_preferred_model,
    build_preferences_dto,
    merge_preferences,
)
from app.modules.config_registry.schemas import ModelConfig
from app.shared.runtime.errors import ConfigurationError


def test_apply_preferred_model_keeps_provider_agnostic_openai_defaults_off_anthropic_targets() -> None:
    model = apply_preferred_model(
        ModelConfig(provider="anthropic", name="claude-sonnet-4"),
        build_preferences_dto(
            default_model_name="gpt-5.4",
            default_reasoning_effort="high",
        ),
    )

    assert model is not None
    assert model.provider == "anthropic"
    assert model.name == "claude-sonnet-4"
    assert model.reasoning_effort is None


def test_apply_preferred_model_keeps_provider_agnostic_unknown_alias_off_anthropic_targets() -> None:
    model = apply_preferred_model(
        ModelConfig(provider="anthropic", name="claude-sonnet-4"),
        build_preferences_dto(
            default_model_name="sonnet-4",
        ),
    )

    assert model is not None
    assert model.provider == "anthropic"
    assert model.name == "claude-sonnet-4"


def test_apply_preferred_model_preserves_provider_agnostic_unknown_models_for_compatible_gateways() -> None:
    model = apply_preferred_model(
        ModelConfig(provider="openai", name="gpt-4.1-mini"),
        build_preferences_dto(
            default_model_name="deepseek-reasoner",
            default_reasoning_effort="high",
        ),
    )

    assert model is not None
    assert model.provider == "openai"
    assert model.name == "deepseek-reasoner"
    assert model.reasoning_effort == "high"


def test_apply_preferred_model_keeps_openai_reasoning_for_flexible_model_choices() -> None:
    model = apply_preferred_model(
        ModelConfig(provider="openai", name="gpt-4.1"),
        build_preferences_dto(
            default_provider="openai",
            default_model_name="gpt-4.1",
            default_reasoning_effort="high",
        ),
    )

    assert model is not None
    assert model.provider == "openai"
    assert model.name == "gpt-4.1"
    assert model.reasoning_effort == "high"
    assert model.thinking_level is None
    assert model.thinking_budget is None


def test_apply_preferred_model_rejects_legacy_shape_conflicts_explicitly() -> None:
    with pytest.raises(
        ConfigurationError,
        match="default_reasoning_effort cannot be combined with "
        "default_thinking_level or default_thinking_budget",
    ):
        apply_preferred_model(
            ModelConfig(provider="gemini", name="gemini-3-pro-preview"),
            build_preferences_dto(
                default_reasoning_effort="high",
                default_thinking_level="low",
            ),
        )


def test_merge_preferences_exposes_legacy_reasoning_conflicts_instead_of_dropping_them() -> None:
    with pytest.raises(
        ConfigurationError,
        match="default_reasoning_effort cannot be combined with "
        "default_thinking_level or default_thinking_budget",
    ):
        merge_preferences(
            build_preferences_dto(
                default_model_name="gpt-5.4",
                default_reasoning_effort="high",
                default_thinking_level="low",
            ),
            build_preferences_dto(default_model_name="gpt-5.4"),
        )


def test_merge_preferences_clears_stale_provider_native_reasoning_when_target_changes() -> None:
    merged = merge_preferences(
        build_preferences_dto(
            default_provider="gemini",
            default_model_name="gemini-2.5-flash",
            default_thinking_budget=0,
        ),
        build_preferences_dto(
            default_provider="openai",
            default_model_name="gpt-4.1",
        ),
    )

    assert merged.default_provider == "openai"
    assert merged.default_model_name == "gpt-4.1"
    assert merged.default_reasoning_effort is None
    assert merged.default_thinking_level is None
    assert merged.default_thinking_budget is None
