from __future__ import annotations

from .dto import AssistantCompactionLevel
from .assistant_runtime_terminal import AssistantRuntimeTerminalError


def resolve_initial_prompt_compaction_level(
    *,
    preserved_recent_message_count: int,
) -> AssistantCompactionLevel:
    if preserved_recent_message_count > 0:
        return "soft"
    return "hard"


def resolve_continuation_compaction_level(
    *,
    original_item_count: int,
    retained_item_count: int,
    dropped_content_item_count: int,
) -> AssistantCompactionLevel:
    if retained_item_count < original_item_count or dropped_content_item_count > 0:
        return "hard"
    return "soft"


def build_compaction_budget_exhausted_error() -> AssistantRuntimeTerminalError:
    return AssistantRuntimeTerminalError(
        code="budget_exhausted",
        message="本轮上下文预算已耗尽，压缩后仍无法继续执行。",
    )


__all__ = [
    "build_compaction_budget_exhausted_error",
    "resolve_continuation_compaction_level",
    "resolve_initial_prompt_compaction_level",
]
