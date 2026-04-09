from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic import model_validator

from app.modules.config_registry.schemas.model_schema import GeminiThinkingLevel, OpenAIReasoningEffort
from app.shared.runtime.llm.llm_reasoning_validation import (
    build_provider_native_reasoning_shape_error,
)

DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS = 4096
PREFERENCES_PROVIDER_MAX_LENGTH = 50
PREFERENCES_MODEL_NAME_MAX_LENGTH = 100
PREFERENCES_MAX_OUTPUT_TOKENS_MIN = 128
PREFERENCES_MAX_OUTPUT_TOKENS_MAX = 131072


class AssistantPreferencesDTO(BaseModel):
    default_provider: str | None = None
    default_model_name: str | None = None
    default_max_output_tokens: int | None = None
    default_reasoning_effort: OpenAIReasoningEffort | None = None
    default_thinking_level: GeminiThinkingLevel | None = None
    default_thinking_budget: int | None = None


class AssistantPreferencesUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_provider: str | None = Field(default=None, max_length=PREFERENCES_PROVIDER_MAX_LENGTH)
    default_model_name: str | None = Field(default=None, max_length=PREFERENCES_MODEL_NAME_MAX_LENGTH)
    default_max_output_tokens: int | None = Field(
        default=None,
        ge=PREFERENCES_MAX_OUTPUT_TOKENS_MIN,
        le=PREFERENCES_MAX_OUTPUT_TOKENS_MAX,
    )
    default_reasoning_effort: OpenAIReasoningEffort | None = None
    default_thinking_level: GeminiThinkingLevel | None = None
    default_thinking_budget: int | None = Field(default=None, ge=-1)

    @model_validator(mode="after")
    def validate_provider_native_reasoning(self) -> "AssistantPreferencesUpdateDTO":
        error = build_provider_native_reasoning_shape_error(
            reasoning_effort=self.default_reasoning_effort,
            thinking_level=self.default_thinking_level,
            thinking_budget=self.default_thinking_budget,
            field_prefix="default_",
        )
        if error is not None:
            raise ValueError(error)
        return self


__all__ = [
    "AssistantPreferencesDTO",
    "AssistantPreferencesUpdateDTO",
    "DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS",
    "PREFERENCES_MAX_OUTPUT_TOKENS_MAX",
    "PREFERENCES_MAX_OUTPUT_TOKENS_MIN",
]
