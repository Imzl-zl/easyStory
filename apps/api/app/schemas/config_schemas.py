from pydantic import BaseModel, Field
from typing import Literal


class ModelConfig(BaseModel):
    provider: str | None = None
    name: str | None = None
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
    max_retry: int = 3
    save_on_step: bool = True
    timeout: int = 300


class NodeConfig(BaseModel):
    id: str
    name: str
    node_type: str = Field(alias="type")
    skill: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    hooks: dict[str, list[str]] = Field(default_factory=dict)
    reviewers: list[str] = Field(default_factory=list)
    auto_proceed: bool = False
    auto_review: bool = False
    auto_fix: bool = False
    max_fix_attempts: int = 3
    on_fix_fail: str = "pause"
    model: ModelConfig | None = None

    model_config = {"populate_by_name": True}


class WorkflowConfig(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings)
    context_injection: ContextInjectionConfig | None = None
    nodes: list[NodeConfig]
