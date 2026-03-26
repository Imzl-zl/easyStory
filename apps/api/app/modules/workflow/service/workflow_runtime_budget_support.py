from __future__ import annotations

from app.shared.runtime.errors import BudgetExceededError, ConfigurationError

from .workflow_runtime_shared import NodeOutcome, ReviewCycleOutcome

BUDGET_PAUSE_REASON = "budget_exceeded"


def build_completed_snapshot(marker: dict[str, int | str]) -> dict[str, list[dict[str, int | str]]]:
    return {"completed_nodes": [marker]}


def ensure_chapter_split_budget_action_supported(budget_error: BudgetExceededError) -> None:
    if budget_error.action == "skip":
        raise ConfigurationError("chapter_split does not support budget.on_exceed=skip")


def build_chapter_split_budget_outcome(
    *,
    completed_snapshot: dict[str, list[dict[str, int | str]]],
    next_node_id: str | None,
    budget_error: BudgetExceededError,
    node_execution_id,
    hook_payload: dict[str, object] | None = None,
) -> NodeOutcome:
    if budget_error.action == "pause":
        return NodeOutcome(
            next_node_id=next_node_id,
            pause_reason=BUDGET_PAUSE_REASON,
            snapshot_extra=completed_snapshot,
            node_execution_id=node_execution_id,
            hook_payload=hook_payload,
        )
    if budget_error.action == "fail":
        return NodeOutcome(
            next_node_id=next_node_id,
            snapshot_extra=completed_snapshot,
            workflow_status="failed",
            node_execution_id=node_execution_id,
            hook_payload=hook_payload,
        )
    raise ConfigurationError("chapter_split does not support budget.on_exceed=skip")


def build_budget_review_outcome(
    budget_error: BudgetExceededError,
    *,
    generated_content: str,
) -> ReviewCycleOutcome:
    final_content = generated_content
    content_source = "generated"
    if budget_error.usage_type == "fix":
        final_content = extract_budget_fix_content(budget_error)
        content_source = "auto_fix"
    if budget_error.action == "pause":
        return ReviewCycleOutcome(
            "pause",
            final_content,
            content_source,
            failure_message=budget_error.message,
            pause_reason=BUDGET_PAUSE_REASON,
        )
    if budget_error.action == "skip":
        return ReviewCycleOutcome(
            "skip",
            final_content,
            content_source,
            failure_message=budget_error.message,
        )
    return ReviewCycleOutcome(
        "fail",
        final_content,
        content_source,
        failure_message=budget_error.message,
    )


def extract_budget_fix_content(budget_error: BudgetExceededError) -> str:
    content = budget_error.raw_output.get("content")
    if not isinstance(content, str):
        raise ConfigurationError("Fix LLM output must be plain text")
    return content
