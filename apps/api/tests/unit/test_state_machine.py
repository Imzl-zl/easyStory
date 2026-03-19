import pytest

from app.modules.workflow.engine import (
    InvalidPauseReasonError,
    InvalidTransitionError,
    WorkflowStateMachine,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("created", "running"),
        ("running", "paused"),
        ("running", "completed"),
        ("running", "failed"),
        ("running", "cancelled"),
        ("paused", "running"),
        ("paused", "cancelled"),
        ("failed", "running"),
    ],
)
def test_validate_transition_accepts_allowed_paths(current: str, target: str) -> None:
    WorkflowStateMachine.validate_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("created", "created"),
        ("created", "paused"),
        ("paused", "completed"),
        ("completed", "running"),
        ("cancelled", "running"),
        ("unknown", "running"),
    ],
)
def test_validate_transition_rejects_invalid_paths(current: str, target: str) -> None:
    with pytest.raises(InvalidTransitionError, match=f"{current} -> {target}"):
        WorkflowStateMachine.validate_transition(current, target)


def test_can_transition_matches_transition_table() -> None:
    assert WorkflowStateMachine.can_transition("running", "paused") is True
    assert WorkflowStateMachine.can_transition("running", "running") is False


@pytest.mark.parametrize("status", ["created", "running", "paused"])
def test_is_active_identifies_active_workflow_states(status: str) -> None:
    assert WorkflowStateMachine.is_active(status) is True


@pytest.mark.parametrize("status", ["completed", "cancelled", "failed"])
def test_is_active_rejects_non_active_states(status: str) -> None:
    assert WorkflowStateMachine.is_active(status) is False


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_is_terminal_identifies_terminal_states(status: str) -> None:
    assert WorkflowStateMachine.is_terminal(status) is True


@pytest.mark.parametrize("status", ["created", "running", "paused", "failed"])
def test_is_terminal_rejects_retryable_or_active_states(status: str) -> None:
    assert WorkflowStateMachine.is_terminal(status) is False


def test_failed_can_retry_to_running() -> None:
    WorkflowStateMachine.validate_transition("failed", "running")


@pytest.mark.parametrize(
    "reason",
    [
        None,
        "user_request",
        "user_interrupted",
        "budget_exceeded",
        "review_failed",
        "error",
        "loop_pause",
        "max_chapters_reached",
    ],
)
def test_validate_pause_reason_accepts_declared_values(reason: str | None) -> None:
    WorkflowStateMachine.validate_pause_reason(reason)


def test_validate_pause_reason_rejects_unknown_value() -> None:
    with pytest.raises(InvalidPauseReasonError, match="unexpected"):
        WorkflowStateMachine.validate_pause_reason("unexpected")


@pytest.mark.parametrize("status", ["completed", "failed", "skipped"])
def test_is_terminal_node_status_identifies_terminal_node_states(status: str) -> None:
    assert WorkflowStateMachine.is_terminal_node_status(status) is True


@pytest.mark.parametrize("status", ["pending", "running", "running_stream", "reviewing", "fixing", "interrupted"])
def test_is_terminal_node_status_rejects_non_terminal_node_states(status: str) -> None:
    assert WorkflowStateMachine.is_terminal_node_status(status) is False


def test_is_interruptible_node_status_only_allows_running_stream() -> None:
    assert WorkflowStateMachine.is_interruptible_node_status("running_stream") is True
    assert WorkflowStateMachine.is_interruptible_node_status("running") is False
