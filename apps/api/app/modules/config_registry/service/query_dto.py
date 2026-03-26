from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from app.modules.config_registry.schemas import (
    BudgetConfig,
    ConfigChangeLogEntry,
    FixStrategy,
    LoopConfig,
    ModelConfig,
    ModelFallbackConfig,
    RetryConfig,
    ReviewConfig,
    SafetyConfig,
    SchemaField,
    StrictSchema,
    WorkflowSettings,
)


AgentType = Literal["writer", "reviewer", "checker"]
HookActionType = Literal["script", "webhook", "agent", "mcp"]
HookEventType = Literal[
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
ContextInjectionType = Literal[
    "project_setting",
    "outline",
    "opening_plan",
    "world_setting",
    "character_profile",
    "chapter_task",
    "previous_chapters",
    "chapter_summary",
    "story_bible",
    "style_reference",
]
WorkflowMode = Literal["manual", "auto"]
WorkflowNodeType = Literal["generate", "review", "export", "custom"]
WorkflowReviewMode = Literal["parallel", "serial"]
WorkflowFixFailAction = Literal["pause", "skip", "fail"]


class ConfigRegistryDTO(StrictSchema):
    pass


class ModelReferenceDTO(ConfigRegistryDTO):
    provider: str | None
    name: str | None
    required_capabilities: list[str]
    temperature: float
    max_tokens: int


class SkillConfigSummaryDTO(ConfigRegistryDTO):
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


class SkillConfigDetailDTO(ConfigRegistryDTO):
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


class AgentConfigSummaryDTO(ConfigRegistryDTO):
    id: str
    name: str
    version: str
    description: str | None
    agent_type: AgentType
    author: str | None
    tags: list[str]
    skill_ids: list[str]
    output_schema_keys: list[str]
    mcp_servers: list[str]
    model: ModelReferenceDTO | None


class AgentConfigDetailDTO(ConfigRegistryDTO):
    id: str
    name: str
    version: str
    description: str | None
    agent_type: AgentType
    author: str | None
    tags: list[str]
    system_prompt: str
    skill_ids: list[str]
    output_schema: dict[str, Any] | None
    mcp_servers: list[str]
    model: ModelConfig | None


class AgentConfigUpdateDTO(AgentConfigDetailDTO):
    pass


class HookTriggerDTO(ConfigRegistryDTO):
    event: HookEventType
    node_types: list[str]


class HookConditionDTO(ConfigRegistryDTO):
    field: str
    operator: str
    value: str | int | bool


class HookActionDTO(ConfigRegistryDTO):
    action_type: HookActionType
    config: dict[str, Any]


class HookRetryDTO(ConfigRegistryDTO):
    max_attempts: int
    delay: int


class HookConfigSummaryDTO(ConfigRegistryDTO):
    id: str
    name: str
    version: str
    description: str | None
    author: str | None
    enabled: bool
    trigger_event: str
    trigger_node_types: list[str]
    action_type: HookActionType
    has_condition: bool
    retry_enabled: bool
    priority: int
    timeout: int


class HookConfigDetailDTO(ConfigRegistryDTO):
    id: str
    name: str
    version: str
    description: str | None
    author: str | None
    enabled: bool
    trigger: HookTriggerDTO
    condition: HookConditionDTO | None
    action: HookActionDTO
    priority: int
    timeout: int
    retry: HookRetryDTO | None


class HookConfigUpdateDTO(HookConfigDetailDTO):
    pass


class ContextInjectionItemDTO(ConfigRegistryDTO):
    inject_type: ContextInjectionType
    required: bool
    count: int | None
    analysis_id: UUID | None
    inject_fields: list[str]


class ContextInjectionRuleDTO(ConfigRegistryDTO):
    node_pattern: str
    inject: list[ContextInjectionItemDTO]


class ContextInjectionConfigDTO(ConfigRegistryDTO):
    enabled: bool
    default_inject: list[ContextInjectionItemDTO]
    rules: list[ContextInjectionRuleDTO]


class WorkflowNodeSummaryDTO(ConfigRegistryDTO):
    id: str
    name: str
    node_type: WorkflowNodeType
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


class WorkflowNodeDetailDTO(ConfigRegistryDTO):
    id: str
    name: str
    node_type: WorkflowNodeType
    skill_id: str | None
    depends_on: list[str]
    hooks: dict[str, list[str]]
    reviewer_ids: list[str]
    auto_proceed: bool | None
    auto_review: bool | None
    auto_fix: bool | None
    review_mode: WorkflowReviewMode
    max_concurrent_reviewers: int
    review_config: ReviewConfig
    max_fix_attempts: int | None
    on_fix_fail: WorkflowFixFailAction
    fix_skill_id: str | None
    fix_strategy: FixStrategy
    loop: LoopConfig
    model: ModelConfig | None
    context_injection: list[ContextInjectionItemDTO]
    input_mapping: dict[str, str]
    formats: list[str]


class WorkflowConfigSummaryDTO(ConfigRegistryDTO):
    id: str
    name: str
    version: str
    description: str | None
    author: str | None
    tags: list[str]
    mode: WorkflowMode
    default_fix_skill: str | None
    default_inject_types: list[str]
    node_count: int
    nodes: list[WorkflowNodeSummaryDTO]
    model: ModelReferenceDTO | None


class WorkflowConfigDetailDTO(ConfigRegistryDTO):
    id: str
    name: str
    version: str
    description: str | None
    author: str | None
    tags: list[str]
    changelog: list[ConfigChangeLogEntry]
    mode: WorkflowMode
    settings: WorkflowSettings
    model: ModelConfig | None
    budget: BudgetConfig
    safety: SafetyConfig
    retry: RetryConfig
    model_fallback: ModelFallbackConfig
    context_injection: ContextInjectionConfigDTO | None
    nodes: list[WorkflowNodeDetailDTO]


class WorkflowConfigUpdateDTO(WorkflowConfigDetailDTO):
    pass
