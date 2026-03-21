from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, Callable, Sequence

from pydantic import ValidationError

from app.modules.config_registry.schemas.config_schemas import AgentConfig

from .contracts import ReviewExecutionFailure, ReviewResult

ReviewOutcome = ReviewResult | ReviewExecutionFailure
IndexedReviewOutcome = tuple[int, ReviewOutcome]


def build_execution_failure(
    reviewer: AgentConfig,
    started_at: float,
    error_type: str,
    message: str,
) -> ReviewExecutionFailure:
    return ReviewExecutionFailure(
        reviewer_id=reviewer.id,
        reviewer_name=reviewer.name,
        error_type=error_type,
        message=message,
        execution_time_ms=elapsed_ms(started_at),
    )


def normalize_review_result(
    raw_result: ReviewResult | dict[str, Any],
    reviewer: AgentConfig,
    started_at: float,
    *,
    error_factory: Callable[[str], Exception],
) -> ReviewResult:
    try:
        result = ReviewResult.model_validate(raw_result)
    except ValidationError as exc:
        raise error_factory(f"Invalid review result from {reviewer.id}: {exc}") from exc
    if result.reviewer_id != reviewer.id:
        raise error_factory(
            f"Reviewer id mismatch: expected {reviewer.id}, got {result.reviewer_id}"
        )
    if result.reviewer_name != reviewer.name:
        raise error_factory(
            f"Reviewer name mismatch: expected {reviewer.name}, got {result.reviewer_name}"
        )
    return result.model_copy(
        update={"execution_time_ms": max(result.execution_time_ms, elapsed_ms(started_at))}
    )


def count_severity(results: Sequence[ReviewResult]) -> dict[str, int]:
    counts = {"critical": 0, "major": 0, "minor": 0}
    for result in results:
        for issue in result.issues:
            if issue.severity in counts:
                counts[issue.severity] += 1
    return counts


def resolve_overall_status(
    results: Sequence[ReviewResult],
    execution_failures: Sequence[ReviewExecutionFailure],
    pass_rule: str,
    critical_count: int,
    *,
    error_factory: Callable[[str], Exception],
) -> str:
    if execution_failures:
        return "failed"
    if pass_rule == "all_pass":
        return "passed" if all(result.status == "passed" for result in results) else "failed"
    if pass_rule == "majority_pass":
        passed_count = sum(1 for result in results if result.status == "passed")
        return "passed" if passed_count > len(results) / 2 else "failed"
    if pass_rule == "no_critical":
        return "passed" if critical_count == 0 else "failed"
    raise error_factory(f"Unsupported pass rule: {pass_rule}")


async def drain_pending_reviews(
    pending: dict[asyncio.Task[ReviewOutcome], int],
) -> list[IndexedReviewOutcome]:
    tasks = list(pending.items())
    if not tasks:
        return []
    for task, _ in tasks:
        task.cancel()
    drained = await asyncio.gather(*(task for task, _ in tasks), return_exceptions=True)
    outcomes: list[IndexedReviewOutcome] = []
    for item, (_, index) in zip(drained, tasks, strict=True):
        if isinstance(item, ReviewResult) or isinstance(item, ReviewExecutionFailure):
            outcomes.append((index, item))
    return outcomes


def ordered_outcomes(indexed_outcomes: Sequence[IndexedReviewOutcome]) -> list[ReviewOutcome]:
    return [outcome for _, outcome in sorted(indexed_outcomes, key=lambda item: item[0])]


def elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


__all__ = [
    "IndexedReviewOutcome",
    "ReviewOutcome",
    "build_execution_failure",
    "count_severity",
    "drain_pending_reviews",
    "elapsed_ms",
    "normalize_review_result",
    "ordered_outcomes",
    "resolve_overall_status",
]
