from __future__ import annotations

from app.modules.config_registry.schemas import ModelConfig
from app.shared.runtime.errors import ConfigurationError

from .preferences_dto import AssistantPreferencesDTO, AssistantPreferencesUpdateDTO


def build_preferences_dto(
    *,
    default_provider: str | None = None,
    default_model_name: str | None = None,
) -> AssistantPreferencesDTO:
    return AssistantPreferencesDTO(
        default_provider=normalize_optional_text(default_provider),
        default_model_name=normalize_optional_text(default_model_name),
    )


def build_updated_preferences(
    payload: AssistantPreferencesUpdateDTO,
) -> AssistantPreferencesDTO:
    return build_preferences_dto(
        default_provider=payload.default_provider,
        default_model_name=payload.default_model_name,
    )


def apply_preferred_model(
    base_model: ModelConfig | None,
    preferences: AssistantPreferencesDTO,
) -> ModelConfig | None:
    if preferences.default_provider is None and preferences.default_model_name is None:
        return base_model
    resolved = base_model.model_copy(deep=True) if base_model is not None else ModelConfig()
    provider = preferences.default_provider
    model_name = preferences.default_model_name
    if provider is not None and provider != resolved.provider:
        return resolved.model_copy(update={"provider": provider, "name": model_name})
    update: dict[str, str | None] = {}
    if provider is not None:
        update["provider"] = provider
    if model_name is not None:
        update["name"] = model_name
    return resolved.model_copy(update=update)


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("Assistant preferences values must be strings")
    normalized = value.strip()
    return normalized or None
