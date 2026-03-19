from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, Awaitable, Callable, Sequence

from pydantic import ValidationError

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import AgentConfig, ReviewConfig
from app.shared.runtime.errors import EasyStoryError

from .contracts import AggregatedReviewResult, ReviewExecutionFailure, ReviewResult

ReviewRunner = Callable[[str, AgentConfig], Awaitable[ReviewResult | dict[str, Any]]]
ReviewOutcome = ReviewResult | ReviewExecutionFailure


class ReviewExecutorError(EasyStoryError):
    """Review execution contract errors."""


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

        async def run(reviewer: AgentConfig) -> ReviewOutcome:
            async with semaphore:
                return await self._execute_single(content, reviewer)

        return list(await asyncio.gather(*(run(reviewer) for reviewer in reviewers)))

    async def _execute_serial(
        self,
        content: str,
        reviewers: Sequence[AgentConfig],
    ) -> list[ReviewOutcome]:
        results: list[ReviewOutcome] = []
        for reviewer in reviewers:
            results.append(await self._execute_single(content, reviewer))
        return results

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
        counts = self._count_severity(results)
        overall_status = self._resolve_overall_status(
            results,
            execution_failures,
            pass_rule,
            counts["critical"],
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
            return self._normalize_result(raw_result, reviewer, started_at)
        except TimeoutError:
            return self._build_execution_failure(
                reviewer,
                started_at,
                "timeout",
                "Reviewer timed out",
            )
        except ReviewExecutorError as exc:
            return self._build_execution_failure(
                reviewer,
                started_at,
                "invalid_result",
                str(exc),
            )
        except Exception as exc:
            return self._build_execution_failure(
                reviewer,
                started_at,
                "execution_error",
                f"Reviewer failed: {exc}",
            )

    def _normalize_result(
        self,
        raw_result: ReviewResult | dict[str, Any],
        reviewer: AgentConfig,
        started_at: float,
    ) -> ReviewResult:
        try:
            result = ReviewResult.model_validate(raw_result)
        except ValidationError as exc:
            raise ReviewExecutorError(f"Invalid review result from {reviewer.id}: {exc}") from exc
        if result.reviewer_id != reviewer.id:
            raise ReviewExecutorError(f"Reviewer id mismatch: expected {reviewer.id}, got {result.reviewer_id}")
        if result.reviewer_name != reviewer.name:
            raise ReviewExecutorError(
                f"Reviewer name mismatch: expected {reviewer.name}, got {result.reviewer_name}"
            )
        duration_ms = self._elapsed_ms(started_at)
        return result.model_copy(update={"execution_time_ms": max(result.execution_time_ms, duration_ms)})

    def _build_execution_failure(
        self,
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
            execution_time_ms=self._elapsed_ms(started_at),
        )

    def _count_severity(self, results: Sequence[ReviewResult]) -> dict[str, int]:
        counts = {"critical": 0, "major": 0, "minor": 0}
        for result in results:
            for issue in result.issues:
                if issue.severity in counts:
                    counts[issue.severity] += 1
        return counts

    def _resolve_overall_status(
        self,
        results: Sequence[ReviewResult],
        execution_failures: Sequence[ReviewExecutionFailure],
        pass_rule: str,
        critical_count: int,
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
        raise ReviewExecutorError(f"Unsupported pass rule: {pass_rule}")

    def _elapsed_ms(self, started_at: float) -> int:
        return int((perf_counter() - started_at) * 1000)
