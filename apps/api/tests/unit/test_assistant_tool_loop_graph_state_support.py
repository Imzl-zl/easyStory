import pytest

from app.modules.assistant.service.tooling.assistant_tool_loop_graph_state_support import (
    TOOL_LOOP_GRAPH_MAX_STEPS_PER_ITERATION,
    TOOL_LOOP_GRAPH_RECURSION_BUFFER,
    resolve_tool_loop_recursion_limit,
)
from app.shared.runtime.errors import ConfigurationError


def test_resolve_tool_loop_recursion_limit_matches_graph_budget_formula() -> None:
    assert resolve_tool_loop_recursion_limit(3) == (
        3 * TOOL_LOOP_GRAPH_MAX_STEPS_PER_ITERATION
        + TOOL_LOOP_GRAPH_RECURSION_BUFFER
    )


def test_resolve_tool_loop_recursion_limit_rejects_non_positive_iterations() -> None:
    with pytest.raises(ConfigurationError, match="max_iterations must be at least 1"):
        resolve_tool_loop_recursion_limit(0)
