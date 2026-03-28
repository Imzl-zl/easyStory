from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.config_registry.schemas import ModelConfig

ASSISTANT_MAX_MESSAGES = 20
ASSISTANT_MESSAGE_MAX_LENGTH = 8000

AssistantMessageRole = Literal["system", "user", "assistant"]


class AssistantMessageDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AssistantMessageRole
    content: str = Field(min_length=1, max_length=ASSISTANT_MESSAGE_MAX_LENGTH)


class AssistantTurnRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str | None = Field(default=None, min_length=1)
    skill_id: str | None = Field(default=None, min_length=1)
    stream: bool = False
    hook_ids: list[str] = Field(default_factory=list)
    project_id: uuid.UUID | None = None
    messages: list[AssistantMessageDTO] = Field(min_length=1, max_length=ASSISTANT_MAX_MESSAGES)
    input_data: dict[str, Any] = Field(default_factory=dict)
    model: ModelConfig | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "AssistantTurnRequestDTO":
        if bool(self.agent_id) == bool(self.skill_id):
            raise ValueError("Exactly one of agent_id or skill_id must be provided")
        return self


class AssistantHookResultDTO(BaseModel):
    event: str
    hook_id: str
    action_type: str
    result: Any


class AssistantTurnResponseDTO(BaseModel):
    agent_id: str | None
    skill_id: str
    provider: str
    model_name: str
    content: str
    hook_results: list[AssistantHookResultDTO] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


__all__ = [
    "ASSISTANT_MAX_MESSAGES",
    "ASSISTANT_MESSAGE_MAX_LENGTH",
    "AssistantHookResultDTO",
    "AssistantMessageDTO",
    "AssistantMessageRole",
    "AssistantTurnRequestDTO",
    "AssistantTurnResponseDTO",
]
