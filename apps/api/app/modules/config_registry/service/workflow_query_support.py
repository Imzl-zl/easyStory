from __future__ import annotations

from app.modules.config_registry.schemas import (
    ContextInjectionConfig,
    ContextInjectionItem,
    ModelConfig,
    NodeConfig,
    WorkflowConfig,
)

from .query_dto import (
    ContextInjectionConfigDTO,
    ContextInjectionItemDTO,
    ContextInjectionRuleDTO,
    WorkflowConfigDetailDTO,
    WorkflowConfigSummaryDTO,
    WorkflowNodeDetailDTO,
    WorkflowNodeSummaryDTO,
)
from .query_support import to_model_reference


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


def to_workflow_detail(workflow: WorkflowConfig) -> WorkflowConfigDetailDTO:
    return WorkflowConfigDetailDTO(
        id=workflow.id,
        name=workflow.name,
        version=workflow.version,
        description=workflow.description,
        author=workflow.author,
        tags=list(workflow.tags),
        changelog=[entry.model_copy(deep=True) for entry in workflow.changelog],
        mode=workflow.mode,
        settings=workflow.settings.model_copy(deep=True),
        model=_copy_model(workflow.model),
        budget=workflow.budget.model_copy(deep=True),
        safety=workflow.safety.model_copy(deep=True),
        retry=workflow.retry.model_copy(deep=True),
        model_fallback=workflow.model_fallback.model_copy(deep=True),
        context_injection=_to_context_injection_config(workflow.context_injection),
        nodes=[to_workflow_node_detail(node) for node in workflow.nodes],
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
        hook_ids=_unique_ordered(hook_id for hook_ids in node.hooks.values() for hook_id in hook_ids),
        context_injection_types=_context_injection_types(node.context_injection),
        auto_proceed=node.auto_proceed,
        auto_review=node.auto_review,
        auto_fix=node.auto_fix,
        fix_skill_id=node.fix_skill,
        loop_enabled=node.loop.enabled,
        formats=list(node.formats),
    )


def to_workflow_node_detail(node: NodeConfig) -> WorkflowNodeDetailDTO:
    return WorkflowNodeDetailDTO(
        id=node.id,
        name=node.name,
        node_type=node.node_type,
        skill_id=node.skill,
        depends_on=list(node.depends_on),
        hooks={stage: list(hook_ids) for stage, hook_ids in node.hooks.items()},
        reviewer_ids=list(node.reviewers),
        auto_proceed=node.auto_proceed,
        auto_review=node.auto_review,
        auto_fix=node.auto_fix,
        review_mode=node.review_mode,
        max_concurrent_reviewers=node.max_concurrent_reviewers,
        review_config=node.review_config.model_copy(deep=True),
        max_fix_attempts=node.max_fix_attempts,
        on_fix_fail=node.on_fix_fail,
        fix_skill_id=node.fix_skill,
        fix_strategy=node.fix_strategy.model_copy(deep=True),
        loop=node.loop.model_copy(deep=True),
        model=_copy_model(node.model),
        context_injection=[_to_context_injection_item(item) for item in node.context_injection],
        input_mapping=dict(node.input_mapping),
        formats=list(node.formats),
    )


def _to_context_injection_config(config: ContextInjectionConfig | None) -> ContextInjectionConfigDTO | None:
    if config is None:
        return None
    return ContextInjectionConfigDTO(
        enabled=config.enabled,
        default_inject=[_to_context_injection_item(item) for item in config.default_inject],
        rules=[
            ContextInjectionRuleDTO(
                node_pattern=rule.node_pattern,
                inject=[_to_context_injection_item(item) for item in rule.inject],
            )
            for rule in config.rules
        ],
    )


def _to_context_injection_item(item: ContextInjectionItem) -> ContextInjectionItemDTO:
    return ContextInjectionItemDTO(
        inject_type=item.inject_type,
        required=item.required,
        count=item.count,
        analysis_id=item.analysis_id,
        inject_fields=list(item.inject_fields),
    )


def _context_injection_types(items: list[ContextInjectionItem]) -> list[str]:
    return _unique_ordered(item.inject_type for item in items)


def _copy_model(model: ModelConfig | None) -> ModelConfig | None:
    if model is None:
        return None
    return model.model_copy(deep=True)


def _unique_ordered(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
