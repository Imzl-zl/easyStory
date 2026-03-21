from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from app.modules.config_registry.schemas.hook_action_config import validate_hook_action_config

from .base_schema import StrictSchema


class HookTrigger(StrictSchema):
    event: Literal[
        "before_workflow_start",
        "after_workflow_end",
        "before_node_start",
        "after_node_end",
        "before_generate",
        "after_generate",
        "before_review",
        "after_review",
        "on_review_fail",
        "before_fix",
        "after_fix",
        "on_error",
    ]
    node_types: list[str] = Field(default_factory=list)


class HookCondition(StrictSchema):
    field: str
    operator: str
    value: str | int | bool


class HookAction(StrictSchema):
    action_type: Literal["script", "webhook", "agent"] = Field(alias="type")
    config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_config(self) -> "HookAction":
        self.config = validate_hook_action_config(self.action_type, self.config)
        return self


class HookRetryConfig(StrictSchema):
    max_attempts: int = 3
    delay: int = 1


class HookConfig(StrictSchema):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    author: str | None = None
    enabled: bool = True
    trigger: HookTrigger
    condition: HookCondition | None = None
    action: HookAction
    priority: int = 10
    timeout: int = 30
    retry: HookRetryConfig | None = None


__all__ = [
    "HookAction",
    "HookCondition",
    "HookConfig",
    "HookRetryConfig",
    "HookTrigger",
]
