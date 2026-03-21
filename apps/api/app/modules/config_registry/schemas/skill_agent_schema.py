from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base_schema import StrictSchema
from .field_schema import SchemaField
from .model_schema import ModelConfig


class SkillConfig(StrictSchema):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    category: str
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    prompt: str
    variables: dict[str, SchemaField] = Field(default_factory=dict)
    inputs: dict[str, SchemaField] = Field(default_factory=dict)
    outputs: dict[str, SchemaField] = Field(default_factory=dict)
    model: ModelConfig | None = None

    @model_validator(mode="after")
    def validate_schema_mode(self) -> "SkillConfig":
        has_simple = bool(self.variables)
        has_enhanced = bool(self.inputs or self.outputs)
        if has_simple and has_enhanced:
            raise ValueError("variables and inputs/outputs are mutually exclusive")
        return self


class AgentConfig(StrictSchema):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    agent_type: Literal["writer", "reviewer", "checker"] = Field(alias="type")
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    system_prompt: str
    skills: list[str] = Field(default_factory=list)
    model: ModelConfig | None = None
    output_schema: dict[str, Any] | None = None
    mcp_servers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_output_schema(self) -> "AgentConfig":
        if self.agent_type == "reviewer" and self.output_schema is not None:
            raise ValueError("reviewer agent cannot define output_schema")
        return self


__all__ = ["AgentConfig", "SkillConfig"]
