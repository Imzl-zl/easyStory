from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.modules.config_registry.schemas import ModelConfig, SchemaField


class ModelReferenceDTO(BaseModel):
    provider: str | None
    name: str | None
    required_capabilities: list[str]
    temperature: float
    max_tokens: int


class SkillConfigSummaryDTO(BaseModel):
    id: str
    name: str
    version: str
    description: str | None
    category: str
    author: str | None
    tags: list[str]
    input_keys: list[str]
    output_keys: list[str]
    model: ModelReferenceDTO | None


class SkillConfigDetailDTO(BaseModel):
    id: str
    name: str
    version: str
    description: str | None
    category: str
    author: str | None
    tags: list[str]
    prompt: str
    variables: dict[str, SchemaField]
    inputs: dict[str, SchemaField]
    outputs: dict[str, SchemaField]
    model: ModelConfig | None


class SkillConfigUpdateDTO(SkillConfigDetailDTO):
    pass


class AgentConfigSummaryDTO(BaseModel):
    id: str
    name: str
    version: str
    description: str | None
    agent_type: str
    author: str | None
    tags: list[str]
    skill_ids: list[str]
    output_schema_keys: list[str]
    mcp_servers: list[str]
    model: ModelReferenceDTO | None


class AgentConfigDetailDTO(BaseModel):
    id: str
    name: str
    version: str
    description: str | None
    agent_type: str
    author: str | None
    tags: list[str]
    system_prompt: str
    skill_ids: list[str]
    output_schema: dict[str, Any] | None
    mcp_servers: list[str]
    model: ModelConfig | None


class AgentConfigUpdateDTO(AgentConfigDetailDTO):
    pass


class HookConfigSummaryDTO(BaseModel):
    id: str
    name: str
    version: str
    description: str | None
    author: str | None
    enabled: bool
    trigger_event: str
    trigger_node_types: list[str]
    action_type: str
    has_condition: bool
    retry_enabled: bool
    priority: int
    timeout: int


class WorkflowNodeSummaryDTO(BaseModel):
    id: str
    name: str
    node_type: str
    skill_id: str | None
    reviewer_ids: list[str]
    depends_on: list[str]
    hook_stages: list[str]
    hook_ids: list[str]
    context_injection_types: list[str]
    auto_proceed: bool | None
    auto_review: bool | None
    auto_fix: bool | None
    fix_skill_id: str | None
    loop_enabled: bool
    formats: list[str]


class WorkflowConfigSummaryDTO(BaseModel):
    id: str
    name: str
    version: str
    description: str | None
    author: str | None
    tags: list[str]
    mode: str
    default_fix_skill: str | None
    default_inject_types: list[str]
    node_count: int
    nodes: list[WorkflowNodeSummaryDTO]
    model: ModelReferenceDTO | None
