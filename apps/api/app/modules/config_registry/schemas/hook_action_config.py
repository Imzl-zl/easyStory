from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictHookConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScriptHookConfig(StrictHookConfig):
    module: str
    function: str
    params: dict[str, Any] = Field(default_factory=dict)


class WebhookHookConfig(StrictHookConfig):
    url: str
    method: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any | None = None


class AgentHookConfig(StrictHookConfig):
    agent_id: str
    input_mapping: dict[str, str] = Field(default_factory=dict)


class McpHookConfig(StrictHookConfig):
    server_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    input_mapping: dict[str, str] = Field(default_factory=dict)


HOOK_ACTION_CONFIGS: dict[str, type[StrictHookConfig]] = {
    "script": ScriptHookConfig,
    "webhook": WebhookHookConfig,
    "agent": AgentHookConfig,
    "mcp": McpHookConfig,
}


def validate_hook_action_config(action_type: str, config: dict[str, Any]) -> dict[str, Any]:
    config_model = HOOK_ACTION_CONFIGS[action_type]
    return config_model.model_validate(config).model_dump()
