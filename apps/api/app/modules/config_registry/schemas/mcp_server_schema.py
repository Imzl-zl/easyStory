from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base_schema import StrictSchema


class McpServerConfig(StrictSchema):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    transport: Literal["streamable_http"] = "streamable_http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: int = 30
    enabled: bool = True


__all__ = ["McpServerConfig"]
