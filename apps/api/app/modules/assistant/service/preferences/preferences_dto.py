from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS = 4096
PREFERENCES_PROVIDER_MAX_LENGTH = 50
PREFERENCES_MODEL_NAME_MAX_LENGTH = 100
PREFERENCES_MAX_OUTPUT_TOKENS_MIN = 128
PREFERENCES_MAX_OUTPUT_TOKENS_MAX = 131072


class AssistantPreferencesDTO(BaseModel):
    default_provider: str | None = None
    default_model_name: str | None = None
    default_max_output_tokens: int | None = None


class AssistantPreferencesUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_provider: str | None = Field(default=None, max_length=PREFERENCES_PROVIDER_MAX_LENGTH)
    default_model_name: str | None = Field(default=None, max_length=PREFERENCES_MODEL_NAME_MAX_LENGTH)
    default_max_output_tokens: int | None = Field(
        default=None,
        ge=PREFERENCES_MAX_OUTPUT_TOKENS_MIN,
        le=PREFERENCES_MAX_OUTPUT_TOKENS_MAX,
    )


__all__ = [
    "AssistantPreferencesDTO",
    "AssistantPreferencesUpdateDTO",
    "DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS",
    "PREFERENCES_MAX_OUTPUT_TOKENS_MAX",
    "PREFERENCES_MAX_OUTPUT_TOKENS_MIN",
]
