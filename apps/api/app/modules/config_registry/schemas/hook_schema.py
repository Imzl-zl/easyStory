from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from app.modules.config_registry.schemas.hook_action_config import validate_hook_action_config

from .base_schema import StrictSchema

WORKFLOW_NODE_HOOK_STAGE_BY_EVENT: dict[str, str] = {
    "before_node_start": "before",
    "before_generate": "before",
    "before_review": "before",
    "before_fix": "before",
    "after_generate": "after",
    "after_review": "after",
    "on_review_fail": "after",
    "after_fix": "after",
    "after_node_end": "after",
    "on_error": "after",
}


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
        "before_assistant_response",
        "after_assistant_response",
        "on_error",
    ]
    node_types: list[str] = Field(default_factory=list)


def expected_workflow_node_hook_stage(event: str) -> str | None:
    return WORKFLOW_NODE_HOOK_STAGE_BY_EVENT.get(event)


class HookCondition(StrictSchema):
    field: str
    operator: str
    value: str | int | bool


class HookAction(StrictSchema):
    action_type: Literal["script", "webhook", "agent", "mcp"] = Field(alias="type")
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
    "expected_workflow_node_hook_stage",
]
