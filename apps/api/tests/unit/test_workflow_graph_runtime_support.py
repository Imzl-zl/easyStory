import pytest

from app.modules.workflow.service.workflow_graph_runtime_support import (
    WORKFLOW_GRAPH_MIN_RECURSION_LIMIT,
    WORKFLOW_GRAPH_RECURSION_BUFFER,
    WORKFLOW_GRAPH_STEPS_PER_NODE_VISIT,
    WORKFLOW_GRAPH_VISIT_BUDGET_PER_CONFIGURED_NODE,
    resolve_workflow_graph_recursion_limit,
)
from app.shared.runtime.errors import ConfigurationError


def test_resolve_workflow_graph_recursion_limit_uses_named_policy_constants() -> None:
    expected = (
        4
        * WORKFLOW_GRAPH_STEPS_PER_NODE_VISIT
        * WORKFLOW_GRAPH_VISIT_BUDGET_PER_CONFIGURED_NODE
        + WORKFLOW_GRAPH_RECURSION_BUFFER
    )
    assert resolve_workflow_graph_recursion_limit(4) == max(
        WORKFLOW_GRAPH_MIN_RECURSION_LIMIT,
        expected,
    )


def test_resolve_workflow_graph_recursion_limit_rejects_empty_graph() -> None:
    with pytest.raises(ConfigurationError, match="requires at least one configured node"):
        resolve_workflow_graph_recursion_limit(0)
