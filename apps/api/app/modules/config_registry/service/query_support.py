from __future__ import annotations

from copy import deepcopy

from app.modules.config_registry.schemas import (
    AgentConfig,
    HookConfig,
    ModelConfig,
    SkillConfig,
)

from .query_dto import (
    AgentConfigDetailDTO,
    AgentConfigSummaryDTO,
    HookActionDTO,
    HookConditionDTO,
    HookConfigDetailDTO,
    HookRetryDTO,
    HookConfigSummaryDTO,
    HookTriggerDTO,
    ModelReferenceDTO,
    SkillConfigDetailDTO,
    SkillConfigSummaryDTO,
)


def to_skill_summary(skill: SkillConfig) -> SkillConfigSummaryDTO:
    declared_inputs = skill.inputs or skill.variables
    return SkillConfigSummaryDTO(
        id=skill.id,
        name=skill.name,
        version=skill.version,
        description=skill.description,
        category=skill.category,
        author=skill.author,
        tags=list(skill.tags),
        input_keys=list(declared_inputs),
        output_keys=list(skill.outputs),
        model=to_model_reference(skill.model),
    )


def to_skill_detail(skill: SkillConfig) -> SkillConfigDetailDTO:
    return SkillConfigDetailDTO(
        id=skill.id,
        name=skill.name,
        version=skill.version,
        description=skill.description,
        category=skill.category,
        author=skill.author,
        tags=list(skill.tags),
        prompt=skill.prompt,
        variables=dict(skill.variables),
        inputs=dict(skill.inputs),
        outputs=dict(skill.outputs),
        model=skill.model,
    )


def to_agent_summary(agent: AgentConfig) -> AgentConfigSummaryDTO:
    output_schema_keys = list(agent.output_schema) if agent.output_schema else []
    return AgentConfigSummaryDTO(
        id=agent.id,
        name=agent.name,
        version=agent.version,
        description=agent.description,
        agent_type=agent.agent_type,
        author=agent.author,
        tags=list(agent.tags),
        skill_ids=list(agent.skills),
        output_schema_keys=output_schema_keys,
        mcp_servers=list(agent.mcp_servers),
        model=to_model_reference(agent.model),
    )


def to_agent_detail(agent: AgentConfig) -> AgentConfigDetailDTO:
    return AgentConfigDetailDTO(
        id=agent.id,
        name=agent.name,
        version=agent.version,
        description=agent.description,
        agent_type=agent.agent_type,
        author=agent.author,
        tags=list(agent.tags),
        system_prompt=agent.system_prompt,
        skill_ids=list(agent.skills),
        output_schema=_copy_output_schema(agent.output_schema),
        mcp_servers=list(agent.mcp_servers),
        model=agent.model,
    )


def to_hook_summary(hook: HookConfig) -> HookConfigSummaryDTO:
    return HookConfigSummaryDTO(
        id=hook.id,
        name=hook.name,
        version=hook.version,
        description=hook.description,
        author=hook.author,
        enabled=hook.enabled,
        trigger_event=hook.trigger.event,
        trigger_node_types=list(hook.trigger.node_types),
        action_type=hook.action.action_type,
        has_condition=hook.condition is not None,
        retry_enabled=hook.retry is not None,
        priority=hook.priority,
        timeout=hook.timeout,
    )


def to_hook_detail(hook: HookConfig) -> HookConfigDetailDTO:
    return HookConfigDetailDTO(
        id=hook.id,
        name=hook.name,
        version=hook.version,
        description=hook.description,
        author=hook.author,
        enabled=hook.enabled,
        trigger=HookTriggerDTO(
            event=hook.trigger.event,
            node_types=list(hook.trigger.node_types),
        ),
        condition=_to_hook_condition(hook),
        action=HookActionDTO(
            action_type=hook.action.action_type,
            config=deepcopy(hook.action.config),
        ),
        priority=hook.priority,
        timeout=hook.timeout,
        retry=_to_hook_retry(hook),
    )


def to_model_reference(model: ModelConfig | None) -> ModelReferenceDTO | None:
    if model is None:
        return None
    return ModelReferenceDTO(
        provider=model.provider,
        name=model.name,
        required_capabilities=list(model.required_capabilities),
        temperature=model.temperature,
        max_tokens=model.max_tokens,
    )


def _to_hook_condition(hook: HookConfig) -> HookConditionDTO | None:
    if hook.condition is None:
        return None
    return HookConditionDTO(
        field=hook.condition.field,
        operator=hook.condition.operator,
        value=hook.condition.value,
    )


def _to_hook_retry(hook: HookConfig) -> HookRetryDTO | None:
    if hook.retry is None:
        return None
    return HookRetryDTO(
        max_attempts=hook.retry.max_attempts,
        delay=hook.retry.delay,
    )

def _copy_output_schema(output_schema: dict | None) -> dict | None:
    if output_schema is None:
        return None
    return deepcopy(output_schema)
