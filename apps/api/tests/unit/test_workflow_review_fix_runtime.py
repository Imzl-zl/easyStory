from types import SimpleNamespace

import pytest

from app.modules.workflow.service.workflow_review_fix_runtime import (
    LangGraphWorkflowReviewFixRuntime,
)
from app.modules.workflow.service.workflow_runtime_shared import ReviewCycleOutcome
from app.shared.runtime.errors import BudgetExceededError


async def _return_async(value):
    return value


def _aggregated(*, overall_status: str, execution_failures: list[object] | None = None):
    return SimpleNamespace(
        overall_status=overall_status,
        execution_failures=execution_failures or [],
    )


@pytest.mark.asyncio
async def test_workflow_review_fix_runtime_skips_review_when_auto_review_disabled() -> None:
    runtime = LangGraphWorkflowReviewFixRuntime(
        generated_content="生成正文",
        generation_budget_error=None,
        build_budget_review_outcome=lambda budget_error, generated_content: ReviewCycleOutcome(
            "pause",
            generated_content,
            "generated",
            failure_message=budget_error.message,
        ),
        resolve_auto_review_enabled=lambda: False,
        load_reviewers=lambda: (_ for _ in ()).throw(AssertionError("should not load reviewers")),
        run_review_round=lambda content, reviewers, review_type: _return_async(None),
        resolve_auto_fix_enabled=lambda: True,
        run_fix_attempt=lambda content, aggregated, attempt, max_attempts: _return_async(content),
        resolve_max_fix_attempts=lambda: 1,
        select_re_reviewers=lambda reviewers, aggregated: reviewers,
        resolve_fix_failure=lambda content: ReviewCycleOutcome("pause", content, "auto_fix"),
        resolve_model_fallback_review_outcome=lambda exc, content, content_source: ReviewCycleOutcome(
            "pause",
            content,
            content_source,
            failure_message=exc.message,
        ),
    )

    outcome = await runtime.run()

    assert outcome == ReviewCycleOutcome("passed", "生成正文", "generated")


@pytest.mark.asyncio
async def test_workflow_review_fix_runtime_pauses_when_auto_fix_disabled() -> None:
    call_log: list[object] = []
    reviewers = ("reviewer-1",)

    runtime = LangGraphWorkflowReviewFixRuntime(
        generated_content="生成正文",
        generation_budget_error=None,
        build_budget_review_outcome=lambda budget_error, generated_content: ReviewCycleOutcome(
            "pause",
            generated_content,
            "generated",
            failure_message=budget_error.message,
        ),
        resolve_auto_review_enabled=lambda: True,
        load_reviewers=lambda: call_log.append("load_reviewers") or reviewers,
        run_review_round=lambda content, resolved_reviewers, review_type: _return_async(
            call_log.append(("review", content, tuple(resolved_reviewers), review_type))
            or _aggregated(overall_status="failed")
        ),
        resolve_auto_fix_enabled=lambda: False,
        run_fix_attempt=lambda content, aggregated, attempt, max_attempts: _return_async(content),
        resolve_max_fix_attempts=lambda: 1,
        select_re_reviewers=lambda resolved_reviewers, aggregated: resolved_reviewers,
        resolve_fix_failure=lambda content: ReviewCycleOutcome("pause", content, "auto_fix"),
        resolve_model_fallback_review_outcome=lambda exc, content, content_source: ReviewCycleOutcome(
            "pause",
            content,
            content_source,
            failure_message=exc.message,
        ),
    )

    outcome = await runtime.run()

    assert outcome == ReviewCycleOutcome(
        "pause",
        "生成正文",
        "generated",
        failure_message="自动审核未通过",
    )
    assert call_log == [
        "load_reviewers",
        ("review", "生成正文", reviewers, "auto_review"),
    ]


@pytest.mark.asyncio
async def test_workflow_review_fix_runtime_runs_fix_and_re_review_until_passed() -> None:
    call_log: list[object] = []
    reviewers = ("reviewer-1", "reviewer-2")
    failed_review = _aggregated(overall_status="failed")
    passed_review = _aggregated(overall_status="passed")

    runtime = LangGraphWorkflowReviewFixRuntime(
        generated_content="生成正文",
        generation_budget_error=None,
        build_budget_review_outcome=lambda budget_error, generated_content: ReviewCycleOutcome(
            "pause",
            generated_content,
            "generated",
            failure_message=budget_error.message,
        ),
        resolve_auto_review_enabled=lambda: True,
        load_reviewers=lambda: reviewers,
        run_review_round=lambda content, resolved_reviewers, review_type: _return_async(
            call_log.append(("review", content, tuple(resolved_reviewers), review_type))
            or (failed_review if review_type == "auto_review" else passed_review)
        ),
        resolve_auto_fix_enabled=lambda: True,
        run_fix_attempt=lambda content, aggregated, attempt, max_attempts: _return_async(
            call_log.append(("fix", content, aggregated, attempt, max_attempts)) or "精修正文"
        ),
        resolve_max_fix_attempts=lambda: 2,
        select_re_reviewers=lambda resolved_reviewers, aggregated: (
            call_log.append(("select_re_reviewers", tuple(resolved_reviewers), aggregated))
            or ("reviewer-2",)
        ),
        resolve_fix_failure=lambda content: ReviewCycleOutcome("pause", content, "auto_fix"),
        resolve_model_fallback_review_outcome=lambda exc, content, content_source: ReviewCycleOutcome(
            "pause",
            content,
            content_source,
            failure_message=exc.message,
        ),
    )

    outcome = await runtime.run()

    assert outcome == ReviewCycleOutcome("passed", "精修正文", "auto_fix")
    assert call_log == [
        ("review", "生成正文", reviewers, "auto_review"),
        ("fix", "生成正文", failed_review, 1, 2),
        ("select_re_reviewers", reviewers, failed_review),
        ("review", "精修正文", ("reviewer-2",), "auto_re_review_1"),
    ]


@pytest.mark.asyncio
async def test_workflow_review_fix_runtime_uses_fix_failure_after_last_attempt() -> None:
    call_log: list[object] = []
    failed_review = _aggregated(overall_status="failed")
    expected_outcome = ReviewCycleOutcome(
        "skip",
        "最终候选",
        "auto_fix",
        failure_message="自动精修达到最大次数，仍未通过审核",
    )

    runtime = LangGraphWorkflowReviewFixRuntime(
        generated_content="生成正文",
        generation_budget_error=None,
        build_budget_review_outcome=lambda budget_error, generated_content: ReviewCycleOutcome(
            "pause",
            generated_content,
            "generated",
            failure_message=budget_error.message,
        ),
        resolve_auto_review_enabled=lambda: True,
        load_reviewers=lambda: ("reviewer-1",),
        run_review_round=lambda content, resolved_reviewers, review_type: _return_async(
            call_log.append(("review", content, review_type)) or failed_review
        ),
        resolve_auto_fix_enabled=lambda: True,
        run_fix_attempt=lambda content, aggregated, attempt, max_attempts: _return_async(
            call_log.append(("fix", content, attempt, max_attempts)) or "最终候选"
        ),
        resolve_max_fix_attempts=lambda: 1,
        select_re_reviewers=lambda resolved_reviewers, aggregated: resolved_reviewers,
        resolve_fix_failure=lambda content: expected_outcome,
        resolve_model_fallback_review_outcome=lambda exc, content, content_source: ReviewCycleOutcome(
            "pause",
            content,
            content_source,
            failure_message=exc.message,
        ),
    )

    outcome = await runtime.run()

    assert outcome == expected_outcome
    assert call_log == [
        ("review", "生成正文", "auto_review"),
        ("fix", "生成正文", 1, 1),
        ("review", "最终候选", "auto_re_review_1"),
    ]


@pytest.mark.asyncio
async def test_workflow_review_fix_runtime_returns_budget_outcome_from_fix_stage() -> None:
    budget_error = BudgetExceededError(
        "预算耗尽",
        action="pause",
        scope="workflow",
        used_tokens=120,
        limit_tokens=100,
        usage_type="fix",
        raw_output={"content": "预算截断后的精修正文"},
    )
    call_log: list[object] = []
    expected_outcome = ReviewCycleOutcome(
        "pause",
        "预算截断后的精修正文",
        "auto_fix",
        failure_message="预算耗尽",
        pause_reason="budget_exceeded",
    )

    runtime = LangGraphWorkflowReviewFixRuntime(
        generated_content="生成正文",
        generation_budget_error=None,
        build_budget_review_outcome=lambda raised_budget_error, generated_content: (
            call_log.append(("budget", raised_budget_error, generated_content)) or expected_outcome
        ),
        resolve_auto_review_enabled=lambda: True,
        load_reviewers=lambda: ("reviewer-1",),
        run_review_round=lambda content, resolved_reviewers, review_type: _return_async(
            _aggregated(overall_status="failed")
        ),
        resolve_auto_fix_enabled=lambda: True,
        run_fix_attempt=lambda content, aggregated, attempt, max_attempts: (_ for _ in ()).throw(
            budget_error
        ),
        resolve_max_fix_attempts=lambda: 1,
        select_re_reviewers=lambda resolved_reviewers, aggregated: resolved_reviewers,
        resolve_fix_failure=lambda content: ReviewCycleOutcome("pause", content, "auto_fix"),
        resolve_model_fallback_review_outcome=lambda exc, content, content_source: ReviewCycleOutcome(
            "pause",
            content,
            content_source,
            failure_message=exc.message,
        ),
    )

    outcome = await runtime.run()

    assert outcome == expected_outcome
    assert call_log == [("budget", budget_error, "生成正文")]
