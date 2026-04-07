from __future__ import annotations

from app.modules.config_registry.schemas import ModelConfig
from app.shared.runtime.errors import ConfigurationError

from .preferences_dto import (
    AssistantPreferencesDTO,
    AssistantPreferencesUpdateDTO,
    PREFERENCES_MAX_OUTPUT_TOKENS_MAX,
    PREFERENCES_MAX_OUTPUT_TOKENS_MIN,
)

DEFAULT_MODEL_MAX_TOKENS = ModelConfig().max_tokens


def build_preferences_dto(
    *,
    default_provider: str | None = None,
    default_model_name: str | None = None,
    default_max_output_tokens: int | None = None,
) -> AssistantPreferencesDTO:
    return AssistantPreferencesDTO(
        default_provider=normalize_optional_text(default_provider),
        default_model_name=normalize_optional_text(default_model_name),
        default_max_output_tokens=normalize_default_max_output_tokens(default_max_output_tokens),
    )


def build_updated_preferences(
    payload: AssistantPreferencesUpdateDTO,
) -> AssistantPreferencesDTO:
    return build_preferences_dto(
        default_provider=payload.default_provider,
        default_model_name=payload.default_model_name,
        default_max_output_tokens=payload.default_max_output_tokens,
    )


def merge_preferences(
    base: AssistantPreferencesDTO,
    override: AssistantPreferencesDTO,
) -> AssistantPreferencesDTO:
    return build_preferences_dto(
        default_provider=override.default_provider or base.default_provider,
        default_model_name=override.default_model_name or base.default_model_name,
        default_max_output_tokens=(
            override.default_max_output_tokens
            if override.default_max_output_tokens is not None
            else base.default_max_output_tokens
        ),
    )


def apply_preferred_model(
    base_model: ModelConfig | None,
    preferences: AssistantPreferencesDTO,
) -> ModelConfig | None:
    if not has_custom_preferences(preferences):
        return base_model
    resolved = base_model.model_copy(deep=True) if base_model is not None else ModelConfig()
    provider = preferences.default_provider
    model_name = preferences.default_model_name
    max_output_tokens = preferences.default_max_output_tokens
    if provider is not None and provider != resolved.provider:
        resolved = resolved.model_copy(update={"provider": provider, "name": model_name})
    else:
        update: dict[str, str | int | None] = {}
        if provider is not None:
            update["provider"] = provider
        if model_name is not None:
            update["name"] = model_name
        if update:
            resolved = resolved.model_copy(update=update)
    if max_output_tokens is not None and _should_apply_preferred_max_tokens(base_model):
        resolved = resolved.model_copy(update={"max_tokens": max_output_tokens})
    return resolved


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("Assistant preferences values must be strings")
    normalized = value.strip()
    return normalized or None


def normalize_default_max_output_tokens(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError("Assistant preferences default_max_output_tokens must be an integer")
    if value < PREFERENCES_MAX_OUTPUT_TOKENS_MIN:
        raise ConfigurationError(
            "Assistant preferences default_max_output_tokens is below the minimum"
        )
    if value > PREFERENCES_MAX_OUTPUT_TOKENS_MAX:
        raise ConfigurationError(
            "Assistant preferences default_max_output_tokens exceeds the maximum"
        )
    return value


def has_custom_preferences(preferences: AssistantPreferencesDTO) -> bool:
    if preferences.default_provider is not None:
        return True
    if preferences.default_model_name is not None:
        return True
    return preferences.default_max_output_tokens is not None


def _should_apply_preferred_max_tokens(base_model: ModelConfig | None) -> bool:
    if base_model is None:
        return True
    return base_model.max_tokens == DEFAULT_MODEL_MAX_TOKENS
