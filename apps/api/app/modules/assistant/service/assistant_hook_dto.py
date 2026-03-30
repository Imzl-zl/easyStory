from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ASSISTANT_HOOK_NAME_MAX_LENGTH = 80
ASSISTANT_HOOK_DESCRIPTION_MAX_LENGTH = 240
AssistantHookEvent = Literal["before_assistant_response", "after_assistant_response"]
AssistantHookActionType = Literal["agent", "mcp"]


def normalize_assistant_hook_name(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("Hook 名称不能为空")
    return normalized


class AssistantAgentHookActionDTO(BaseModel):
    action_type: Literal["agent"] = "agent"
    agent_id: str = Field(min_length=1)
    input_mapping: dict[str, str] = Field(default_factory=dict)


class AssistantMcpHookActionDTO(BaseModel):
    action_type: Literal["mcp"] = "mcp"
    server_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    input_mapping: dict[str, str] = Field(default_factory=dict)


AssistantHookActionDTO = Annotated[
    AssistantAgentHookActionDTO | AssistantMcpHookActionDTO,
    Field(discriminator="action_type"),
]


class AssistantHookSummaryDTO(BaseModel):
    id: str
    file_name: str | None = None
    name: str
    description: str | None = None
    enabled: bool
    event: AssistantHookEvent
    action: AssistantHookActionDTO
    updated_at: datetime | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_hook_name(value)


class AssistantHookDetailDTO(AssistantHookSummaryDTO):
    pass


class AssistantHookCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    name: str = Field(min_length=1, max_length=ASSISTANT_HOOK_NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=ASSISTANT_HOOK_DESCRIPTION_MAX_LENGTH)
    event: AssistantHookEvent
    action: AssistantHookActionDTO

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_hook_name(value)


class AssistantHookUpdateDTO(AssistantHookCreateDTO):
    pass


__all__ = [
    "ASSISTANT_HOOK_DESCRIPTION_MAX_LENGTH",
    "ASSISTANT_HOOK_NAME_MAX_LENGTH",
    "AssistantAgentHookActionDTO",
    "AssistantHookActionDTO",
    "AssistantHookActionType",
    "AssistantHookCreateDTO",
    "AssistantHookDetailDTO",
    "AssistantHookEvent",
    "AssistantHookSummaryDTO",
    "AssistantHookUpdateDTO",
    "AssistantMcpHookActionDTO",
    "normalize_assistant_hook_name",
]
