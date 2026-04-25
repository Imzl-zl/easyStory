from __future__ import annotations

from app.shared.runtime.errors import ConfigurationError

WORKFLOW_GRAPH_STEPS_PER_NODE_VISIT = 2
WORKFLOW_GRAPH_VISIT_BUDGET_PER_CONFIGURED_NODE = 2
WORKFLOW_GRAPH_VISIT_BUDGET_PER_RUNTIME_LOOP_ITEM = 1
WORKFLOW_GRAPH_RECURSION_BUFFER = 10
WORKFLOW_GRAPH_MIN_RECURSION_LIMIT = 25


def resolve_workflow_graph_recursion_limit(
    configured_node_count: int,
    *,
    runtime_loop_item_count: int = 0,
) -> int:
    if configured_node_count < 1:
        raise ConfigurationError("Workflow graph requires at least one configured node")
    if runtime_loop_item_count < 0:
        raise ConfigurationError("Workflow graph runtime loop item count cannot be negative")
    planned_visits = (
        configured_node_count * WORKFLOW_GRAPH_VISIT_BUDGET_PER_CONFIGURED_NODE
        + runtime_loop_item_count * WORKFLOW_GRAPH_VISIT_BUDGET_PER_RUNTIME_LOOP_ITEM
    )
    planned_steps = planned_visits * WORKFLOW_GRAPH_STEPS_PER_NODE_VISIT
    return max(
        WORKFLOW_GRAPH_MIN_RECURSION_LIMIT,
        planned_steps + WORKFLOW_GRAPH_RECURSION_BUFFER,
    )
