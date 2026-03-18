from pydantic import BaseModel, Field, model_validator
from typing import Literal


class ModelConfig(BaseModel):
    provider: str | None = None
    name: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: list[str] | None = None


class SkillVariable(BaseModel):
    var_type: str = Field(alias="type")
    required: bool = False
    description: str | None = None
    default: str | int | bool | None = None

    model_config = {"populate_by_name": True}


class SkillConfig(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    category: str
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    prompt: str
    variables: dict[str, SkillVariable] = Field(default_factory=dict)
    model: ModelConfig | None = None


class AgentConfig(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    agent_type: str = Field(alias="type")
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    system_prompt: str
    skills: list[str] = Field(default_factory=list)
    model: ModelConfig | None = None

    model_config = {"populate_by_name": True}


class HookTrigger(BaseModel):
    event: str
    node_types: list[str] = Field(default_factory=list)


class HookCondition(BaseModel):
    field: str
    operator: str
    value: str | int | bool


class HookAction(BaseModel):
    action_type: str = Field(alias="type")
    config: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class HookRetryConfig(BaseModel):
    max_attempts: int = 3
    delay: int = 1


class HookConfig(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    enabled: bool = True
    trigger: HookTrigger
    condition: HookCondition | None = None
    action: HookAction
    priority: int = 10
    timeout: int = 30
    retry: HookRetryConfig | None = None


class ContextInjectionItem(BaseModel):
    inject_type: str = Field(alias="type")
    required: bool = False
    count: int | None = None

    model_config = {"populate_by_name": True}


class ContextInjectionRule(BaseModel):
    node_pattern: str
    inject: list[ContextInjectionItem] = Field(default_factory=list)


class ContextInjectionConfig(BaseModel):
    enabled: bool = True
    rules: list[ContextInjectionRule] = Field(default_factory=list)


class WorkflowSettings(BaseModel):
    auto_proceed: bool = False
    auto_review: bool = False
    auto_fix: bool = False
    save_on_step: bool = True
    default_pass_rule: Literal["all_pass", "majority_pass", "no_critical"] = "no_critical"


class BudgetConfig(BaseModel):
    max_tokens_per_node: int = 50000
    max_tokens_per_workflow: int = 500000
    max_tokens_per_day: int = 2000000
    max_tokens_per_day_per_user: int | None = None
    warning_threshold: float = 0.8
    on_exceed: Literal["pause", "skip", "fail"] = "pause"


class SafetyConfig(BaseModel):
    max_retry_per_node: int = 3
    max_fix_attempts: int = 3
    max_total_retries: int = 10
    execution_timeout: int = 3600
    node_timeout: int = 300


class RetryConfig(BaseModel):
    strategy: Literal["exponential_backoff", "fixed", "none"] = "exponential_backoff"
    initial_delay: float = 1.0
    max_delay: float = 30.0
    max_attempts: int = 3
    retryable_errors: list[str] = Field(
        default_factory=lambda: ["timeout", "rate_limit", "server_error"]
    )


class ModelFallbackItem(BaseModel):
    model: str


class ModelFallbackConfig(BaseModel):
    enabled: bool = False
    chain: list[ModelFallbackItem] = Field(default_factory=list)
    on_all_fail: Literal["pause", "fail", "skip"] = "pause"


class LoopPauseConfig(BaseModel):
    strategy: Literal["none", "every", "every_n"] = "none"
    every_n: int | None = None

    @model_validator(mode="after")
    def validate_pause_config(self) -> "LoopPauseConfig":
        if self.strategy == "every_n":
            if self.every_n is None or self.every_n < 1:
                raise ValueError(
                    "loop.pause.every_n must be >= 1 when loop.pause.strategy is 'every_n'"
                )
        elif self.every_n is not None:
            raise ValueError(
                "loop.pause.every_n is only allowed when loop.pause.strategy is 'every_n'"
            )
        return self


class LoopConfig(BaseModel):
    enabled: bool = False
    count_from: str | None = None
    item_var: str = "chapter_index"
    pause: LoopPauseConfig | None = None


class ReviewConfig(BaseModel):
    pass_rule: Literal["all_pass", "majority_pass", "no_critical"] = "no_critical"
    re_review_scope: Literal["all", "failed_only"] = "all"


class FixStrategy(BaseModel):
    mode: Literal["targeted", "full_rewrite"] = "targeted"
    selection_rule: Literal["auto", "targeted", "full_rewrite"] = "auto"
    targeted_threshold: int = 3
    rewrite_threshold: int = 6


class NodeConfig(BaseModel):
    id: str
    name: str
    node_type: str = Field(alias="type")
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

    model_config = {"populate_by_name": True}


class WorkflowConfig(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    mode: Literal["manual", "auto"]
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings)
    model: ModelConfig | None = None
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    model_fallback: ModelFallbackConfig = Field(default_factory=ModelFallbackConfig)
    context_injection: ContextInjectionConfig | None = None
    nodes: list[NodeConfig]
