from __future__ import annotations

from app.modules.config_registry.schemas import StrictSchema


class McpServerConfigSummaryDTO(StrictSchema):
    id: str
    name: str
    version: str
    description: str | None
    transport: str
    url: str
    timeout: int
    enabled: bool
    header_count: int


class McpServerConfigDetailDTO(StrictSchema):
    id: str
    name: str
    version: str
    description: str | None
    transport: str
    url: str
    headers: dict[str, str]
    timeout: int
    enabled: bool


class McpServerConfigUpdateDTO(McpServerConfigDetailDTO):
    pass


__all__ = [
    "McpServerConfigDetailDTO",
    "McpServerConfigSummaryDTO",
    "McpServerConfigUpdateDTO",
]
