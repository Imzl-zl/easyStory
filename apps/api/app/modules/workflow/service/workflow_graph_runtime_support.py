from __future__ import annotations

from app.shared.runtime.errors import ConfigurationError

WORKFLOW_GRAPH_STEPS_PER_NODE_VISIT = 2
WORKFLOW_GRAPH_VISIT_BUDGET_PER_CONFIGURED_NODE = 2
WORKFLOW_GRAPH_RECURSION_BUFFER = 10
WORKFLOW_GRAPH_MIN_RECURSION_LIMIT = 25


def resolve_workflow_graph_recursion_limit(configured_node_count: int) -> int:
    if configured_node_count < 1:
        raise ConfigurationError("Workflow graph requires at least one configured node")
    planned_steps = (
        configured_node_count
        * WORKFLOW_GRAPH_STEPS_PER_NODE_VISIT
        * WORKFLOW_GRAPH_VISIT_BUDGET_PER_CONFIGURED_NODE
    )
    return max(
        WORKFLOW_GRAPH_MIN_RECURSION_LIMIT,
        planned_steps + WORKFLOW_GRAPH_RECURSION_BUFFER,
    )
