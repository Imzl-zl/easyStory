from __future__ import annotations

from copy import deepcopy

from app.modules.config_registry.schemas import (
    AgentConfig,
    ContextInjectionItem,
    HookConfig,
    ModelConfig,
    NodeConfig,
    SkillConfig,
    WorkflowConfig,
)

from .query_dto import (
    AgentConfigDetailDTO,
    AgentConfigSummaryDTO,
    HookConfigSummaryDTO,
    ModelReferenceDTO,
    SkillConfigDetailDTO,
    SkillConfigSummaryDTO,
    WorkflowConfigSummaryDTO,
    WorkflowNodeSummaryDTO,
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


def to_workflow_summary(workflow: WorkflowConfig) -> WorkflowConfigSummaryDTO:
    return WorkflowConfigSummaryDTO(
        id=workflow.id,
        name=workflow.name,
        version=workflow.version,
        description=workflow.description,
        author=workflow.author,
        tags=list(workflow.tags),
        mode=workflow.mode,
        default_fix_skill=workflow.settings.default_fix_skill,
        default_inject_types=_context_injection_types(
            workflow.context_injection.default_inject if workflow.context_injection else []
        ),
        node_count=len(workflow.nodes),
        nodes=[to_workflow_node_summary(node) for node in workflow.nodes],
        model=to_model_reference(workflow.model),
    )


def to_workflow_node_summary(node: NodeConfig) -> WorkflowNodeSummaryDTO:
    return WorkflowNodeSummaryDTO(
        id=node.id,
        name=node.name,
        node_type=node.node_type,
        skill_id=node.skill,
        reviewer_ids=list(node.reviewers),
        depends_on=list(node.depends_on),
        hook_stages=list(node.hooks),
        hook_ids=_flatten_hook_ids(node),
        context_injection_types=_context_injection_types(node.context_injection),
        auto_proceed=node.auto_proceed,
        auto_review=node.auto_review,
        auto_fix=node.auto_fix,
        fix_skill_id=node.fix_skill,
        loop_enabled=node.loop.enabled,
        formats=list(node.formats),
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


def _context_injection_types(items: list[ContextInjectionItem]) -> list[str]:
    return _unique_ordered(item.inject_type for item in items)


def _flatten_hook_ids(node: NodeConfig) -> list[str]:
    return _unique_ordered(hook_id for hook_ids in node.hooks.values() for hook_id in hook_ids)


def _copy_output_schema(output_schema: dict | None) -> dict | None:
    if output_schema is None:
        return None
    return deepcopy(output_schema)


def _unique_ordered(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
