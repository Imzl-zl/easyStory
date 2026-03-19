from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from .hook_action_config import validate_hook_action_config


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

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


class SchemaField(StrictSchema):
    field_type: Literal["string", "integer", "boolean", "array", "object"] = Field(alias="type")
    required: bool = False
    description: str | None = None
    default: Any | None = None
    enum: list[Any] = Field(default_factory=list)
    min: int | float | None = None
    max: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    items: SchemaField | None = None
    properties: dict[str, SchemaField] = Field(default_factory=dict)


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


class ContextInjectionItem(StrictSchema):
    inject_type: str = Field(alias="type")
    required: bool = False
    count: int | None = None


class ContextInjectionRule(StrictSchema):
    node_pattern: str
    inject: list[ContextInjectionItem] = Field(default_factory=list)


class ContextInjectionConfig(StrictSchema):
    enabled: bool = True
    default_inject: list[ContextInjectionItem] = Field(default_factory=list)
    rules: list[ContextInjectionRule] = Field(default_factory=list)


class WorkflowSettings(StrictSchema):
    auto_proceed: bool = False
    auto_review: bool = False
    auto_fix: bool = False
    save_on_step: bool = True
    default_pass_rule: Literal["all_pass", "majority_pass", "no_critical"] = "no_critical"
    default_fix_skill: str | None = None


class BudgetConfig(StrictSchema):
    max_tokens_per_node: int = 50000
    max_tokens_per_workflow: int = 500000
    max_tokens_per_day: int = 2000000
    max_tokens_per_day_per_user: int | None = None
    warning_threshold: float = 0.8
    on_exceed: Literal["pause", "skip", "fail"] = "pause"


class SafetyConfig(StrictSchema):
    max_retry_per_node: int = 3
    max_fix_attempts: int = 3
    max_total_retries: int = 10
    execution_timeout: int = 3600
    node_timeout: int = 300


class RetryConfig(StrictSchema):
    strategy: Literal["exponential_backoff", "fixed", "none"] = "exponential_backoff"
    initial_delay: float = 1.0
    max_delay: float = 30.0
    max_attempts: int = 3
    retryable_errors: list[str] = Field(
        default_factory=lambda: ["timeout", "rate_limit", "server_error"]
    )


class ModelFallbackItem(StrictSchema):
    model: str


class ModelFallbackConfig(StrictSchema):
    enabled: bool = False
    chain: list[ModelFallbackItem] = Field(default_factory=list)
    on_all_fail: Literal["pause", "fail"] = "pause"


class LoopPauseConfig(StrictSchema):
    strategy: Literal["none", "every", "every_n"] = "none"
    every_n: int | None = None

    @model_validator(mode="after")
    def validate_pause_config(self) -> "LoopPauseConfig":
        if self.strategy == "every_n" and (self.every_n is None or self.every_n < 1):
            raise ValueError("every_n must be >= 1 when pause.strategy is every_n")
        if self.strategy != "every_n" and self.every_n is not None:
            raise ValueError("every_n is only allowed when pause.strategy is every_n")
        return self


class LoopConfig(StrictSchema):
    enabled: bool = False
    count_from: str | None = None
    item_var: str = "chapter_index"
    pause: LoopPauseConfig | None = None


class ReviewConfig(StrictSchema):
    pass_rule: Literal["all_pass", "majority_pass", "no_critical"] = "no_critical"
    re_review_scope: Literal["all", "failed_only"] = "all"


class FixStrategy(StrictSchema):
    selection_rule: Literal["auto", "targeted", "full_rewrite"] = "auto"
    targeted_threshold: int = 3
    rewrite_threshold: int = 6


class NodeConfig(StrictSchema):
    id: str
    name: str
    node_type: Literal["generate", "review", "export", "custom"] = Field(alias="type")
    skill: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    hooks: dict[str, list[str]] = Field(default_factory=dict)
    reviewers: list[str] = Field(default_factory=list)
    auto_proceed: bool | None = None
    auto_review: bool | None = None
    auto_fix: bool | None = None
    review_mode: Literal["parallel", "serial"] = "serial"
    max_concurrent_reviewers: int = 3
    review_config: ReviewConfig = Field(default_factory=ReviewConfig)
    max_fix_attempts: int | None = None
    on_fix_fail: Literal["pause", "skip", "fail"] = "pause"
    fix_skill: str | None = None
    fix_strategy: FixStrategy = Field(default_factory=FixStrategy)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    model: ModelConfig | None = None
    context_injection: list[ContextInjectionItem] = Field(default_factory=list)
    input_mapping: dict[str, str] = Field(default_factory=dict)
    formats: list[Literal["txt", "markdown", "docx"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_node_shape(self) -> "NodeConfig":
        if self.node_type == "generate" and not self.skill:
            raise ValueError("generate node requires skill")
        if self.node_type == "review" and not self.reviewers:
            raise ValueError("review node requires reviewers")
        if self.node_type == "export" and not self.formats:
            raise ValueError("export node requires formats")
        if self.node_type == "custom":
            raise ValueError("custom node is not supported in v0.1")
        return self


class ConfigChangeLogEntry(StrictSchema):
    version: str
    date: str
    changes: str


class WorkflowConfig(StrictSchema):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    changelog: list[ConfigChangeLogEntry] = Field(default_factory=list)
    mode: Literal["manual", "auto"]
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings)
    model: ModelConfig | None = None
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    model_fallback: ModelFallbackConfig = Field(default_factory=ModelFallbackConfig)
    context_injection: ContextInjectionConfig | None = None
    nodes: list[NodeConfig]

    @model_validator(mode="after")
    def validate_workflow(self) -> "WorkflowConfig":
        node_ids = {node.id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("workflow node ids must be unique")
        for node in self.nodes:
            missing = [dep for dep in node.depends_on if dep not in node_ids]
            if missing:
                raise ValueError(f"node {node.id} depends on missing nodes: {missing}")
        return self
