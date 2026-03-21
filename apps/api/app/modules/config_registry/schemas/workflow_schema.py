from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base_schema import StrictSchema
from .model_schema import ModelConfig


class ContextInjectionItem(StrictSchema):
    inject_type: Literal[
        "project_setting",
        "outline",
        "opening_plan",
        "chapter_task",
        "previous_chapters",
        "story_bible",
    ] = Field(alias="type")
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


__all__ = [
    "BudgetConfig",
    "ConfigChangeLogEntry",
    "ContextInjectionConfig",
    "ContextInjectionItem",
    "ContextInjectionRule",
    "FixStrategy",
    "LoopConfig",
    "LoopPauseConfig",
    "ModelFallbackConfig",
    "ModelFallbackItem",
    "NodeConfig",
    "RetryConfig",
    "ReviewConfig",
    "SafetyConfig",
    "WorkflowConfig",
    "WorkflowSettings",
]
