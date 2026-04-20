from __future__ import annotations

from app.modules.config_registry.schemas import ModelConfig
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.llm_reasoning_validation import (
    build_provider_native_reasoning_error,
    build_provider_native_reasoning_shape_error,
)

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
    default_reasoning_effort: str | None = None,
    default_thinking_level: str | None = None,
    default_thinking_budget: int | None = None,
) -> AssistantPreferencesDTO:
    return AssistantPreferencesDTO(
        default_provider=normalize_optional_text(default_provider),
        default_model_name=normalize_optional_text(default_model_name),
        default_max_output_tokens=normalize_default_max_output_tokens(default_max_output_tokens),
        default_reasoning_effort=normalize_optional_text(default_reasoning_effort),
        default_thinking_level=normalize_optional_text(default_thinking_level),
        default_thinking_budget=normalize_optional_thinking_budget(default_thinking_budget),
    )


def build_updated_preferences(
    payload: AssistantPreferencesUpdateDTO,
) -> AssistantPreferencesDTO:
    return build_preferences_dto(
        default_provider=payload.default_provider,
        default_model_name=payload.default_model_name,
        default_max_output_tokens=payload.default_max_output_tokens,
        default_reasoning_effort=payload.default_reasoning_effort,
        default_thinking_level=payload.default_thinking_level,
        default_thinking_budget=payload.default_thinking_budget,
    )


def merge_preferences(
    base: AssistantPreferencesDTO,
    override: AssistantPreferencesDTO,
) -> AssistantPreferencesDTO:
    resolved_provider, resolved_model_name = _resolve_merged_preference_target(base, override)
    resolved_reasoning_effort, resolved_thinking_level, resolved_thinking_budget = (
        _merge_provider_native_reasoning(
            base,
            override,
            resolved_provider=resolved_provider,
        )
    )
    return build_preferences_dto(
        default_provider=resolved_provider,
        default_model_name=resolved_model_name,
        default_max_output_tokens=(
            override.default_max_output_tokens
            if override.default_max_output_tokens is not None
            else base.default_max_output_tokens
        ),
        default_reasoning_effort=resolved_reasoning_effort,
        default_thinking_level=resolved_thinking_level,
        default_thinking_budget=resolved_thinking_budget,
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
        if model_name is not None and _should_apply_provider_agnostic_model(base_model, model_name):
            update["name"] = model_name
        if update:
            resolved = resolved.model_copy(update=update)
    if max_output_tokens is not None and _should_apply_preferred_max_tokens(base_model):
        resolved = resolved.model_copy(update={"max_tokens": max_output_tokens})
    reasoning_update = _resolve_provider_native_reasoning_update(
        resolved,
        preferences=preferences,
    )
    if reasoning_update:
        resolved = resolved.model_copy(update=reasoning_update)
    return resolved


def validate_preferences_provider_native_reasoning(
    preferences: AssistantPreferencesDTO,
) -> None:
    error = build_provider_native_reasoning_error(
        provider=preferences.default_provider,
        reasoning_effort=preferences.default_reasoning_effort,
        thinking_level=preferences.default_thinking_level,
        thinking_budget=preferences.default_thinking_budget,
        field_prefix="default_",
    )
    if error is not None:
        raise BusinessRuleError(error)


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
    if preferences.default_max_output_tokens is not None:
        return True
    if preferences.default_reasoning_effort is not None:
        return True
    if preferences.default_thinking_level is not None:
        return True
    return preferences.default_thinking_budget is not None


def has_provider_native_reasoning_preferences(preferences: AssistantPreferencesDTO) -> bool:
    return any(
        (
            preferences.default_reasoning_effort is not None,
            preferences.default_thinking_level is not None,
            preferences.default_thinking_budget is not None,
        )
    )


def normalize_optional_thinking_budget(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError("Assistant preferences default_thinking_budget must be an integer")
    if value < -1:
        raise ConfigurationError(
            "Assistant preferences default_thinking_budget cannot be less than -1"
        )
    return value


def _should_apply_preferred_max_tokens(base_model: ModelConfig | None) -> bool:
    if base_model is None:
        return True
    return base_model.max_tokens == DEFAULT_MODEL_MAX_TOKENS


def _merge_provider_native_reasoning(
    base: AssistantPreferencesDTO,
    override: AssistantPreferencesDTO,
    *,
    resolved_provider: str | None,
) -> tuple[str | None, str | None, int | None]:
    if override.default_reasoning_effort is not None:
        return override.default_reasoning_effort, None, None
    if override.default_thinking_level is not None:
        return None, override.default_thinking_level, None
    if override.default_thinking_budget is not None:
        return None, None, override.default_thinking_budget
    inherited_reasoning = (
        base.default_reasoning_effort,
        base.default_thinking_level,
        base.default_thinking_budget,
    )
    if inherited_reasoning == (None, None, None):
        return inherited_reasoning
    shape_error = build_provider_native_reasoning_shape_error(
        reasoning_effort=inherited_reasoning[0],
        thinking_level=inherited_reasoning[1],
        thinking_budget=inherited_reasoning[2],
        field_prefix="default_",
    )
    if shape_error is not None:
        raise ConfigurationError(shape_error)
    error = build_provider_native_reasoning_error(
        provider=resolved_provider,
        reasoning_effort=inherited_reasoning[0],
        thinking_level=inherited_reasoning[1],
        thinking_budget=inherited_reasoning[2],
        field_prefix="default_",
    )
    if error is not None:
        return (None, None, None)
    return inherited_reasoning


def _resolve_provider_native_reasoning_update(
    resolved_model: ModelConfig,
    *,
    preferences: AssistantPreferencesDTO,
) -> dict[str, str | int | None]:
    reasoning_effort = preferences.default_reasoning_effort
    thinking_level = preferences.default_thinking_level
    thinking_budget = preferences.default_thinking_budget
    if (
        reasoning_effort is None
        and thinking_level is None
        and thinking_budget is None
    ):
        return {}
    shape_error = build_provider_native_reasoning_shape_error(
        reasoning_effort=reasoning_effort,
        thinking_level=thinking_level,
        thinking_budget=thinking_budget,
        field_prefix="default_",
    )
    if shape_error is not None:
        raise ConfigurationError(shape_error)
    if preferences.default_provider is not None:
        error = build_provider_native_reasoning_error(
            provider=preferences.default_provider,
            reasoning_effort=reasoning_effort,
            thinking_level=thinking_level,
            thinking_budget=thinking_budget,
            field_prefix="default_",
        )
        if error is not None:
            raise ConfigurationError(error)
    if not _should_apply_provider_native_reasoning(
        resolved_model,
        reasoning_effort=reasoning_effort,
        thinking_level=thinking_level,
        thinking_budget=thinking_budget,
    ):
        return {}
    if reasoning_effort is not None:
        return {
            "reasoning_effort": reasoning_effort,
            "thinking_budget": None,
            "thinking_level": None,
        }
    if thinking_level is not None:
        return {
            "reasoning_effort": None,
            "thinking_budget": None,
            "thinking_level": thinking_level,
        }
    return {
        "reasoning_effort": None,
        "thinking_budget": thinking_budget,
        "thinking_level": None,
    }


def _should_apply_provider_native_reasoning(
    model: ModelConfig,
    *,
    reasoning_effort: str | None,
    thinking_level: str | None,
    thinking_budget: int | None,
) -> bool:
    family = _resolve_model_family(provider=model.provider, model_name=model.name)
    if reasoning_effort is not None:
        return family in {None, "openai"}
    if thinking_level is not None or thinking_budget is not None:
        return family in {None, "gemini"}
    return False


def _should_apply_provider_agnostic_model(
    base_model: ModelConfig | None,
    preferred_model_name: str,
) -> bool:
    if base_model is None:
        return True
    preferred_family = _resolve_model_family(
        provider=None,
        model_name=preferred_model_name,
    )
    base_family = _resolve_model_family(
        provider=base_model.provider,
        model_name=base_model.name,
    )
    if base_family == "anthropic":
        return preferred_family == "anthropic"
    if base_family == "gemini":
        return preferred_family == "gemini"
    if preferred_family is None or base_family is None:
        return True
    return preferred_family == base_family


def _resolve_merged_preference_target(
    base: AssistantPreferencesDTO,
    override: AssistantPreferencesDTO,
) -> tuple[str | None, str | None]:
    if (
        override.default_provider is not None
        and override.default_provider != base.default_provider
    ):
        return override.default_provider, override.default_model_name
    return (
        override.default_provider or base.default_provider,
        override.default_model_name or base.default_model_name,
    )


def _resolve_model_family(
    *,
    provider: str | None,
    model_name: str | None,
) -> str | None:
    normalized_provider = normalize_optional_text(provider)
    normalized_model_name = normalize_optional_text(model_name)
    if normalized_model_name is not None:
        lowered_model_name = normalized_model_name.lower()
        if lowered_model_name.startswith("gpt-"):
            return "openai"
        if lowered_model_name.startswith("gemini-"):
            return "gemini"
        if lowered_model_name.startswith("claude-"):
            return "anthropic"
    if normalized_provider is None:
        return None
    lowered_provider = normalized_provider.lower()
    if lowered_provider in {"openai", "gemini", "anthropic"}:
        return lowered_provider
    return None
