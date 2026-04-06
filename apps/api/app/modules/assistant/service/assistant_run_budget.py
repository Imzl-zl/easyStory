from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from app.shared.runtime.errors import ConfigurationError

from .assistant_tool_runtime_dto import AssistantToolDescriptor

DEFAULT_ASSISTANT_MAX_PARALLEL_TOOL_CALLS = 1


@dataclass(frozen=True)
class AssistantRunBudget:
    max_steps: int
    max_tool_calls: int | None = None
    max_input_tokens: int | None = None
    max_history_tokens: int | None = None
    max_tool_schema_tokens: int | None = None
    max_tool_result_tokens_per_step: int | None = None
    max_read_bytes: int | None = None
    max_write_bytes: int | None = None
    max_parallel_tool_calls: int = DEFAULT_ASSISTANT_MAX_PARALLEL_TOOL_CALLS
    tool_timeout_seconds: int | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


def build_assistant_run_budget(
    *,
    max_steps: int,
    visible_descriptors: tuple[AssistantToolDescriptor, ...],
) -> AssistantRunBudget:
    if max_steps < 1:
        raise ConfigurationError("Assistant run budget max_steps must be >= 1")
    max_tool_calls = max_steps
    return AssistantRunBudget(
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
        max_parallel_tool_calls=DEFAULT_ASSISTANT_MAX_PARALLEL_TOOL_CALLS,
        tool_timeout_seconds=_resolve_tool_timeout_seconds(visible_descriptors),
    )


def enrich_assistant_run_budget_with_input_window(
    budget: AssistantRunBudget | None,
    *,
    context_window_tokens: int | None,
    max_output_tokens: int | None,
) -> AssistantRunBudget | None:
    if context_window_tokens is None:
        return budget
    if max_output_tokens is not None and context_window_tokens <= max_output_tokens:
        raise ConfigurationError(
            "Assistant model output budget exceeds or matches the resolved context window"
        )
    base_budget = budget or AssistantRunBudget(
        max_steps=1,
        max_parallel_tool_calls=DEFAULT_ASSISTANT_MAX_PARALLEL_TOOL_CALLS,
    )
    if max_output_tokens is None:
        return replace(
            base_budget,
            max_input_tokens=context_window_tokens,
        )
    return replace(
        base_budget,
        max_input_tokens=context_window_tokens - max_output_tokens,
    )


def _resolve_tool_timeout_seconds(
    visible_descriptors: tuple[AssistantToolDescriptor, ...],
) -> int | None:
    if not visible_descriptors:
        return None
    if any(item.mutability == "write" for item in visible_descriptors):
        return None
    return max(item.timeout_seconds for item in visible_descriptors)
