from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

PREFERENCES_PROVIDER_MAX_LENGTH = 50
PREFERENCES_MODEL_NAME_MAX_LENGTH = 100


class AssistantPreferencesDTO(BaseModel):
    default_provider: str | None = None
    default_model_name: str | None = None


class AssistantPreferencesUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_provider: str | None = Field(default=None, max_length=PREFERENCES_PROVIDER_MAX_LENGTH)
    default_model_name: str | None = Field(default=None, max_length=PREFERENCES_MODEL_NAME_MAX_LENGTH)


__all__ = ["AssistantPreferencesDTO", "AssistantPreferencesUpdateDTO"]
