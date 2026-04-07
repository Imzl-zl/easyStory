from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ASSISTANT_MCP_NAME_MAX_LENGTH = 80
ASSISTANT_MCP_DESCRIPTION_MAX_LENGTH = 240
ASSISTANT_MCP_URL_MAX_LENGTH = 2000
ASSISTANT_MCP_VERSION_MAX_LENGTH = 40
ASSISTANT_MCP_TIMEOUT_MIN = 1
ASSISTANT_MCP_TIMEOUT_MAX = 600


def normalize_assistant_mcp_name(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("MCP 名称不能为空")
    return normalized


class AssistantMcpSummaryDTO(BaseModel):
    id: str
    file_name: str | None = None
    name: str
    description: str | None = None
    enabled: bool
    version: str
    transport: str
    url: str
    timeout: int
    header_count: int
    updated_at: datetime | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_mcp_name(value)


class AssistantMcpDetailDTO(AssistantMcpSummaryDTO):
    headers: dict[str, str] = Field(default_factory=dict)


class AssistantMcpCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    name: str = Field(min_length=1, max_length=ASSISTANT_MCP_NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=ASSISTANT_MCP_DESCRIPTION_MAX_LENGTH)
    version: str = Field(default="1.0.0", min_length=1, max_length=ASSISTANT_MCP_VERSION_MAX_LENGTH)
    transport: str = Field(default="streamable_http")
    url: str = Field(min_length=1, max_length=ASSISTANT_MCP_URL_MAX_LENGTH)
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(
        default=30,
        ge=ASSISTANT_MCP_TIMEOUT_MIN,
        le=ASSISTANT_MCP_TIMEOUT_MAX,
    )

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        return normalize_assistant_mcp_name(value)


class AssistantMcpUpdateDTO(AssistantMcpCreateDTO):
    pass


__all__ = [
    "ASSISTANT_MCP_DESCRIPTION_MAX_LENGTH",
    "ASSISTANT_MCP_NAME_MAX_LENGTH",
    "ASSISTANT_MCP_TIMEOUT_MAX",
    "ASSISTANT_MCP_TIMEOUT_MIN",
    "ASSISTANT_MCP_URL_MAX_LENGTH",
    "ASSISTANT_MCP_VERSION_MAX_LENGTH",
    "AssistantMcpCreateDTO",
    "AssistantMcpDetailDTO",
    "AssistantMcpSummaryDTO",
    "AssistantMcpUpdateDTO",
    "normalize_assistant_mcp_name",
]
