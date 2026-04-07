from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


ASSISTANT_SKILL_NAME_MAX_LENGTH = 80
ASSISTANT_SKILL_DESCRIPTION_MAX_LENGTH = 240
ASSISTANT_SKILL_CONTENT_MAX_LENGTH = 12000


def normalize_assistant_skill_name(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("Skill 名称不能为空")
    return normalized


class AssistantSkillSummaryDTO(BaseModel):
    id: str
    file_name: str | None = None
    name: str
    description: str | None = None
    enabled: bool
    updated_at: datetime | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_skill_name(value)


class AssistantSkillDetailDTO(AssistantSkillSummaryDTO):
    content: str
    default_provider: str | None = None
    default_model_name: str | None = None
    default_max_output_tokens: int | None = None


class AssistantSkillCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    name: str = Field(min_length=1, max_length=ASSISTANT_SKILL_NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=ASSISTANT_SKILL_DESCRIPTION_MAX_LENGTH)
    content: str = Field(min_length=1, max_length=ASSISTANT_SKILL_CONTENT_MAX_LENGTH)
    default_provider: str | None = None
    default_model_name: str | None = None
    default_max_output_tokens: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_skill_name(value)


class AssistantSkillUpdateDTO(AssistantSkillCreateDTO):
    pass


__all__ = [
    "ASSISTANT_SKILL_CONTENT_MAX_LENGTH",
    "ASSISTANT_SKILL_DESCRIPTION_MAX_LENGTH",
    "ASSISTANT_SKILL_NAME_MAX_LENGTH",
    "AssistantSkillCreateDTO",
    "AssistantSkillDetailDTO",
    "AssistantSkillSummaryDTO",
    "AssistantSkillUpdateDTO",
    "normalize_assistant_skill_name",
]
