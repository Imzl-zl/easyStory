from __future__ import annotations

from app.shared.runtime.errors import EasyStoryError


class InvalidTransitionError(EasyStoryError):
    def __init__(self, current: str, target: str):
        super().__init__(f"Invalid transition: {current} -> {target}")
        self.current = current
        self.target = target


class InvalidPauseReasonError(EasyStoryError):
    def __init__(self, reason: str):
        super().__init__(f"Invalid pause reason: {reason}")
        self.reason = reason


class WorkflowStateMachine:
    VALID_TRANSITIONS: dict[str, frozenset[str]] = {
        "created": frozenset({"running"}),
        "running": frozenset({"paused", "completed", "failed", "cancelled"}),
        "paused": frozenset({"running", "cancelled"}),
        "failed": frozenset({"running"}),
        "completed": frozenset(),
        "cancelled": frozenset(),
    }
    ACTIVE_STATES = frozenset({"created", "running", "paused"})
    TERMINAL_STATES = frozenset({"completed", "cancelled"})
    PAUSE_REASONS = frozenset(
        {
            "user_request",
            "user_interrupted",
            "budget_exceeded",
            "review_failed",
            "model_fallback_exhausted",
            "error",
            "loop_pause",
            "max_chapters_reached",
        }
    )
    NODE_TERMINAL_STATES = frozenset({"completed", "failed", "skipped"})
    INTERRUPTIBLE_NODE_STATES = frozenset({"running_stream"})

    @classmethod
    def validate_transition(cls, current: str, target: str) -> None:
        if not cls.can_transition(current, target):
            raise InvalidTransitionError(current, target)

    @classmethod
    def can_transition(cls, current: str, target: str) -> bool:
        return target in cls.VALID_TRANSITIONS.get(current, frozenset())

    @classmethod
    def is_active(cls, status: str) -> bool:
        return status in cls.ACTIVE_STATES

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in cls.TERMINAL_STATES

    @classmethod
    def validate_pause_reason(cls, reason: str | None) -> None:
        if reason is None:
            return
        if reason not in cls.PAUSE_REASONS:
            raise InvalidPauseReasonError(reason)

    @classmethod
    def is_terminal_node_status(cls, status: str) -> bool:
        return status in cls.NODE_TERMINAL_STATES

    @classmethod
    def is_interruptible_node_status(cls, status: str) -> bool:
        return status in cls.INTERRUPTIBLE_NODE_STATES
