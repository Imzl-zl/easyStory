from __future__ import annotations

from typing import Any

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import (
    AgentConfig,
    HookConfig,
    NodeConfig,
    SkillConfig,
    WorkflowConfig,
)
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import ConfigurationError

from .dto import WorkflowExecutionDTO, WorkflowNodeSummaryDTO

PREPARATION_NODE_IDS = frozenset({"outline", "opening_plan"})


def resolve_start_node_id(workflow_config: WorkflowConfig) -> str:
    for node in workflow_config.nodes:
        if node.id not in PREPARATION_NODE_IDS:
            return node.id
    raise ConfigurationError(
        f"Workflow {workflow_config.id} has no executable node after preparation"
    )


def freeze_workflow(
    config_loader: ConfigLoader,
    workflow_config: WorkflowConfig,
) -> dict[str, Any]:
    snapshot = dump_config(workflow_config)
    hooks = freeze_hooks(config_loader, workflow_config)
    if hooks:
        snapshot["resolved_hooks"] = hooks
    return snapshot


def freeze_hooks(
    config_loader: ConfigLoader,
    workflow_config: WorkflowConfig,
) -> dict[str, Any]:
    hook_ids = {
        hook_id
        for node in workflow_config.nodes
        for hook_ids in node.hooks.values()
        for hook_id in hook_ids
    }
    return {
        hook_id: dump_config(config_loader.load_hook(hook_id))
        for hook_id in sorted(hook_ids)
    }


def freeze_agents(
    config_loader: ConfigLoader,
    workflow_config: WorkflowConfig,
) -> list[AgentConfig]:
    agent_ids = {
        reviewer
        for node in workflow_config.nodes
        for reviewer in node.reviewers
    }
    return [config_loader.load_agent(agent_id) for agent_id in sorted(agent_ids)]


def freeze_skills(
    config_loader: ConfigLoader,
    workflow_config: WorkflowConfig,
    agents: list[AgentConfig],
) -> dict[str, Any]:
    skill_ids = collect_skill_ids(workflow_config, agents)
    return {
        skill_id: dump_config(config_loader.load_skill(skill_id))
        for skill_id in sorted(skill_ids)
    }


def collect_skill_ids(
    workflow_config: WorkflowConfig,
    agents: list[AgentConfig],
) -> set[str]:
    skill_ids = {
        skill_id
        for node in workflow_config.nodes
        for skill_id in (node.skill, node.fix_skill)
        if skill_id
    }
    if workflow_config.settings.default_fix_skill is not None:
        skill_ids.add(workflow_config.settings.default_fix_skill)
    for agent in agents:
        skill_ids.update(agent.skills)
    return skill_ids


def build_runtime_snapshot(
    workflow: WorkflowExecution,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    snapshot: dict[str, Any] = {}
    if workflow.current_node_id is not None:
        snapshot["current_node_id"] = workflow.current_node_id
    if workflow.resume_from_node is not None:
        snapshot["resume_from_node"] = workflow.resume_from_node
    if workflow.pause_reason is not None:
        snapshot["pause_reason"] = workflow.pause_reason
    if extra:
        snapshot.update(extra)
    return snapshot or None


def load_workflow_snapshot(snapshot: dict[str, Any]) -> WorkflowConfig:
    normalized = {
        key: value
        for key, value in snapshot.items()
        if key in WorkflowConfig.model_fields
    }
    return WorkflowConfig.model_validate(normalized)


def load_skill_snapshot(
    skills_snapshot: dict[str, Any],
    skill_id: str | None,
) -> SkillConfig:
    if skill_id is None:
        raise ConfigurationError("Node is missing skill id")
    raw = skills_snapshot.get(skill_id)
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Skill snapshot not found: {skill_id}")
    return SkillConfig.model_validate(raw)


def load_agent_snapshot(
    agents_snapshot: dict[str, Any],
    agent_id: str,
) -> AgentConfig:
    raw = agents_snapshot.get(agent_id)
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Agent snapshot not found: {agent_id}")
    return AgentConfig.model_validate(raw)


def resolve_node_config(
    workflow_config: WorkflowConfig,
    node_id: str | None,
) -> NodeConfig:
    if node_id is None:
        raise ConfigurationError("Workflow current_node_id is not set")
    for node in workflow_config.nodes:
        if node.id == node_id:
            return node
    raise ConfigurationError(f"Workflow node not found in snapshot: {node_id}")


def resolve_node_order(snapshot: dict[str, Any], node_id: str) -> int:
    nodes = parse_nodes(snapshot)
    for index, node in enumerate(nodes):
        if node.id == node_id:
            return index
    raise ConfigurationError(f"Workflow node not found in snapshot: {node_id}")


def workflow_to_dto(workflow: WorkflowExecution) -> WorkflowExecutionDTO:
    workflow_snapshot = workflow.workflow_snapshot or {}
    nodes = parse_nodes(workflow_snapshot)
    return WorkflowExecutionDTO(
        execution_id=workflow.id,
        project_id=workflow.project_id,
        template_id=workflow.template_id,
        workflow_id=string_value(workflow_snapshot.get("id")),
        workflow_name=string_value(workflow_snapshot.get("name")),
        workflow_version=string_value(workflow_snapshot.get("version")),
        mode=mode_value(workflow_snapshot.get("mode")),
        status=workflow.status,
        current_node_id=workflow.current_node_id,
        current_node_name=resolve_node_name(workflow.current_node_id, nodes),
        pause_reason=workflow.pause_reason,
        resume_from_node=workflow.resume_from_node,
        has_runtime_snapshot=workflow.snapshot is not None,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        nodes=nodes,
    )


def parse_nodes(snapshot: dict[str, Any]) -> list[WorkflowNodeSummaryDTO]:
    raw_nodes = snapshot.get("nodes")
    if not isinstance(raw_nodes, list):
        return []
    return [to_node_summary(node) for node in raw_nodes if isinstance(node, dict)]


def to_node_summary(node: dict[str, Any]) -> WorkflowNodeSummaryDTO:
    return WorkflowNodeSummaryDTO(
        id=string_value(node.get("id")) or "",
        name=string_value(node.get("name")) or "",
        node_type=string_value(node.get("node_type") or node.get("type")) or "",
        depends_on=string_list(node.get("depends_on")),
    )


def resolve_node_name(
    current_node_id: str | None,
    nodes: list[WorkflowNodeSummaryDTO],
) -> str | None:
    for node in nodes:
        if node.id == current_node_id:
            return node.name
    return None


def resolve_next_node_id(
    snapshot: dict[str, Any],
    *,
    current_node_id: str,
) -> str | None:
    nodes = parse_nodes(snapshot)
    for index, node in enumerate(nodes):
        if node.id != current_node_id:
            continue
        next_index = index + 1
        if next_index >= len(nodes):
            return None
        return nodes[next_index].id
    return None


def dump_config(
    config: WorkflowConfig | SkillConfig | AgentConfig | HookConfig,
) -> dict[str, Any]:
    return config.model_dump(mode="json", exclude_none=True)


def string_value(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def mode_value(value: Any) -> str | None:
    if value in {"manual", "auto"}:
        return value
    return None


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
