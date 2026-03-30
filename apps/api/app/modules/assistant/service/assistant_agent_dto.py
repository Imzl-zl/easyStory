from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


ASSISTANT_AGENT_NAME_MAX_LENGTH = 80
ASSISTANT_AGENT_DESCRIPTION_MAX_LENGTH = 240
ASSISTANT_AGENT_PROMPT_MAX_LENGTH = 12000


def normalize_assistant_agent_name(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("Agent 名称不能为空")
    return normalized


class AssistantAgentSummaryDTO(BaseModel):
    id: str
    file_name: str | None = None
    name: str
    description: str | None = None
    enabled: bool
    skill_id: str
    updated_at: datetime | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_agent_name(value)


class AssistantAgentDetailDTO(AssistantAgentSummaryDTO):
    skill_id: str
    system_prompt: str
    default_provider: str | None = None
    default_model_name: str | None = None
    default_max_output_tokens: int | None = None


class AssistantAgentCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    name: str = Field(min_length=1, max_length=ASSISTANT_AGENT_NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=ASSISTANT_AGENT_DESCRIPTION_MAX_LENGTH)
    skill_id: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1, max_length=ASSISTANT_AGENT_PROMPT_MAX_LENGTH)
    default_provider: str | None = None
    default_model_name: str | None = None
    default_max_output_tokens: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_agent_name(value)


class AssistantAgentUpdateDTO(AssistantAgentCreateDTO):
    pass


__all__ = [
    "ASSISTANT_AGENT_DESCRIPTION_MAX_LENGTH",
    "ASSISTANT_AGENT_NAME_MAX_LENGTH",
    "ASSISTANT_AGENT_PROMPT_MAX_LENGTH",
    "AssistantAgentCreateDTO",
    "AssistantAgentDetailDTO",
    "AssistantAgentSummaryDTO",
    "AssistantAgentUpdateDTO",
    "normalize_assistant_agent_name",
]
