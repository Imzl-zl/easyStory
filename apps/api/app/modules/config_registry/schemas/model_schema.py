from __future__ import annotations

from pydantic import Field

from .base_schema import StrictSchema


class ModelConfig(StrictSchema):
    provider: str | None = None
    name: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: list[str] | None = None


__all__ = ["ModelConfig"]
