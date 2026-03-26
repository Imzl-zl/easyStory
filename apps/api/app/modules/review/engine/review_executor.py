from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, Awaitable, Callable, Sequence

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import AgentConfig, ReviewConfig
from app.shared.runtime.errors import BudgetExceededError, EasyStoryError, ModelFallbackExhaustedError

from .contracts import AggregatedReviewResult, ReviewExecutionFailure, ReviewResult
from .review_executor_support import (
    IndexedReviewOutcome,
    ReviewOutcome,
    build_execution_failure,
    count_severity,
    drain_pending_reviews,
    normalize_review_result,
    ordered_outcomes,
    resolve_overall_status,
)

ReviewRunner = Callable[[str, AgentConfig], Awaitable[ReviewResult | dict[str, Any]]]


class ReviewExecutorError(EasyStoryError):
    """Review execution contract errors."""


class _ReviewBudgetInterruption(Exception):
    def __init__(
        self,
        budget_error: BudgetExceededError,
        outcomes: Sequence[IndexedReviewOutcome],
    ) -> None:
        super().__init__(budget_error.message)
        self.budget_error = budget_error
        self.outcomes = tuple(outcomes)


class ReviewExecutor:
    """Review orchestration belongs to the review module."""

    def __init__(
        self,
        review_runner: ReviewRunner,
        *,
        config_loader: ConfigLoader | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ReviewExecutorError("timeout_seconds must be > 0")
        self.review_runner = review_runner
        self.config_loader = config_loader
        self.timeout_seconds = timeout_seconds

    async def execute_review(
        self,
        content: str,
        reviewers: Sequence[str | AgentConfig],
        mode: str,
        config: ReviewConfig,
        *,
        max_concurrent_reviewers: int = 3,
    ) -> AggregatedReviewResult:
        resolved_reviewers = self._resolve_reviewers(reviewers)
        try:
            if mode == "parallel":
                results = await self._execute_parallel(
                    content,
                    resolved_reviewers,
                    max_concurrent_reviewers,
                )
            elif mode == "serial":
                results = await self._execute_serial(content, resolved_reviewers)
            else:
                raise ReviewExecutorError(f"Unsupported review mode: {mode}")
        except _ReviewBudgetInterruption as exc:
            exc.budget_error.partial_aggregated_review = self._build_partial_aggregate(
                exc.outcomes,
                config.pass_rule,
            )
            raise exc.budget_error
        return self.aggregate(results, config.pass_rule)

    async def _execute_parallel(
        self,
        content: str,
        reviewers: Sequence[AgentConfig],
        max_concurrent_reviewers: int,
    ) -> list[ReviewOutcome]:
        if max_concurrent_reviewers < 1:
            raise ReviewExecutorError("max_concurrent_reviewers must be >= 1")
        semaphore = asyncio.Semaphore(max_concurrent_reviewers)
        completed: list[IndexedReviewOutcome] = []

        async def run(reviewer: AgentConfig) -> ReviewOutcome:
            async with semaphore:
                return await self._execute_single(content, reviewer)

        pending = {
            asyncio.create_task(run(reviewer)): index
            for index, reviewer in enumerate(reviewers)
        }
        while pending:
            done, _ = await asyncio.wait(tuple(pending), return_when=asyncio.FIRST_COMPLETED)
            budget_error: BudgetExceededError | None = None
            for task in done:
                index = pending.pop(task)
                try:
                    completed.append((index, task.result()))
                except BudgetExceededError as exc:
                    if budget_error is None:
                        budget_error = exc
            if budget_error is None:
                continue
            completed.extend(await drain_pending_reviews(pending))
            raise _ReviewBudgetInterruption(budget_error, completed)
        return ordered_outcomes(completed)

    async def _execute_serial(
        self,
        content: str,
        reviewers: Sequence[AgentConfig],
    ) -> list[ReviewOutcome]:
        completed: list[IndexedReviewOutcome] = []
        for index, reviewer in enumerate(reviewers):
            try:
                outcome = await self._execute_single(content, reviewer)
            except BudgetExceededError as exc:
                raise _ReviewBudgetInterruption(exc, completed) from exc
            completed.append((index, outcome))
        return ordered_outcomes(completed)

    def aggregate(
        self,
        outcomes: Sequence[ReviewOutcome],
        pass_rule: str,
    ) -> AggregatedReviewResult:
        if not outcomes:
            raise ReviewExecutorError("Review outcomes cannot be empty")
        results = [outcome for outcome in outcomes if isinstance(outcome, ReviewResult)]
        execution_failures = [
            outcome for outcome in outcomes if isinstance(outcome, ReviewExecutionFailure)
        ]
        counts = count_severity(results)
        overall_status = resolve_overall_status(
            results,
            execution_failures,
            pass_rule,
            counts["critical"],
            error_factory=ReviewExecutorError,
        )
        return AggregatedReviewResult(
            overall_status=overall_status,
            results=results,
            execution_failures=execution_failures,
            total_issues=sum(len(result.issues) for result in results),
            critical_count=counts["critical"],
            major_count=counts["major"],
            minor_count=counts["minor"],
            pass_rule=pass_rule,
        )

    def _build_partial_aggregate(
        self,
        indexed_outcomes: Sequence[IndexedReviewOutcome],
        pass_rule: str,
    ) -> AggregatedReviewResult | None:
        if not indexed_outcomes:
            return None
        return self.aggregate(ordered_outcomes(indexed_outcomes), pass_rule)

    def _resolve_reviewers(self, reviewers: Sequence[str | AgentConfig]) -> list[AgentConfig]:
        if not reviewers:
            raise ReviewExecutorError("At least one reviewer is required")
        resolved = [self._resolve_reviewer(reviewer) for reviewer in reviewers]
        for reviewer in resolved:
            if reviewer.agent_type != "reviewer":
                raise ReviewExecutorError(f"Agent is not a reviewer: {reviewer.id}")
        return resolved

    def _resolve_reviewer(self, reviewer: str | AgentConfig) -> AgentConfig:
        if isinstance(reviewer, AgentConfig):
            return reviewer
        if self.config_loader is None:
            raise ReviewExecutorError("config_loader is required when reviewers are passed as ids")
        return self.config_loader.load_agent(reviewer)

    async def _execute_single(self, content: str, reviewer: AgentConfig) -> ReviewOutcome:
        started_at = perf_counter()
        try:
            raw_result = await asyncio.wait_for(
                self.review_runner(content, reviewer),
                timeout=self.timeout_seconds,
            )
            return normalize_review_result(
                raw_result,
                reviewer,
                started_at,
                error_factory=ReviewExecutorError,
            )
        except TimeoutError:
            return build_execution_failure(
                reviewer,
                started_at,
                "timeout",
                "Reviewer timed out",
            )
        except ReviewExecutorError as exc:
            return build_execution_failure(
                reviewer,
                started_at,
                "invalid_result",
                str(exc),
            )
        except BudgetExceededError:
            raise
        except ModelFallbackExhaustedError:
            raise
        except Exception as exc:
            return build_execution_failure(
                reviewer,
                started_at,
                "execution_error",
                f"Reviewer failed: {exc}",
            )
