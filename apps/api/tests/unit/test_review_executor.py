import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import AgentConfig, ReviewConfig
from app.modules.review.engine import (
    ReviewExecutionFailure,
    ReviewExecutor,
    ReviewExecutorError,
    ReviewIssue,
    ReviewResult,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


async def test_execute_review_parallel_timeout_is_aggregated_predictably() -> None:
    reviewers = [
        _build_reviewer("agent.fast", "快速审核"),
        _build_reviewer("agent.slow", "慢速审核"),
    ]

    async def runner(content: str, reviewer: AgentConfig):
        assert content == "章节正文"
        if reviewer.id == "agent.slow":
            await asyncio.sleep(0.05)
        return _passed_result(reviewer)

    executor = ReviewExecutor(runner, timeout_seconds=0.01)

    aggregated = await executor.execute_review(
        "章节正文",
        reviewers,
        "parallel",
        ReviewConfig(pass_rule="no_critical"),
        max_concurrent_reviewers=2,
    )

    assert [item.reviewer_id for item in aggregated.results] == ["agent.fast"]
    assert aggregated.results[0].status == "passed"
    assert aggregated.execution_failures == [
        ReviewExecutionFailure(
            reviewer_id="agent.slow",
            reviewer_name="慢速审核",
            error_type="timeout",
            message="Reviewer timed out",
            execution_time_ms=aggregated.execution_failures[0].execution_time_ms,
        )
    ]
    assert aggregated.total_issues == 0
    assert aggregated.critical_count == 0
    assert aggregated.overall_status == "failed"


async def test_execute_review_serial_preserves_order() -> None:
    reviewers = [
        _build_reviewer("agent.first", "审核一"),
        _build_reviewer("agent.second", "审核二"),
    ]
    execution_order: list[str] = []

    async def runner(content: str, reviewer: AgentConfig):
        execution_order.append(reviewer.id)
        await asyncio.sleep(0)
        return _passed_result(reviewer)

    executor = ReviewExecutor(runner)
    aggregated = await executor.execute_review(
        "正文",
        reviewers,
        "serial",
        ReviewConfig(pass_rule="all_pass"),
    )

    assert execution_order == ["agent.first", "agent.second"]
    assert [item.reviewer_id for item in aggregated.results] == execution_order
    assert aggregated.overall_status == "passed"


def test_aggregate_supports_majority_and_no_critical() -> None:
    reviewer = _build_reviewer("agent.style_checker", "文风检查员")

    async def runner(content: str, config: AgentConfig):
        return _passed_result(config)

    executor = ReviewExecutor(runner)
    passed = _passed_result(reviewer)
    warning = _warning_result(reviewer, "建议优化")
    failed_major = _failed_result(reviewer, "存在 major 问题", "major")
    failed_critical = _failed_result(reviewer, "存在 critical 问题", "critical")

    majority = executor.aggregate([passed, passed, warning], "majority_pass")
    assert majority.overall_status == "passed"

    no_critical = executor.aggregate([passed, failed_major], "no_critical")
    assert no_critical.overall_status == "passed"
    assert no_critical.major_count == 1

    critical = executor.aggregate([passed, failed_critical], "no_critical")
    assert critical.overall_status == "failed"
    assert critical.critical_count == 1


async def test_execute_review_invalid_result_becomes_execution_failure() -> None:
    reviewer = _build_reviewer("agent.style_checker", "文风检查员")

    async def runner(content: str, config: AgentConfig):
        assert content == "正文"
        return {
            "reviewer_id": reviewer.id,
            "reviewer_name": reviewer.name,
            "status": "passed",
            "issues": [
                {
                    "category": "style_deviation",
                    "severity": "minor",
                    "description": "passed 不能带问题",
                }
            ],
            "summary": "非法结果",
            "execution_time_ms": 1,
            "tokens_used": 1,
        }

    executor = ReviewExecutor(runner)
    aggregated = await executor.execute_review(
        "正文",
        [reviewer],
        "serial",
        ReviewConfig(pass_rule="all_pass"),
    )

    assert aggregated.results == []
    assert aggregated.execution_failures[0].error_type == "invalid_result"
    assert "passed review result cannot contain issues" in aggregated.execution_failures[0].message
    assert aggregated.overall_status == "failed"


def test_review_result_rejects_failed_without_blocking_issue() -> None:
    reviewer = _build_reviewer("agent.style_checker", "文风检查员")

    with pytest.raises(ValidationError, match="failed review result"):
        ReviewResult(
            reviewer_id=reviewer.id,
            reviewer_name=reviewer.name,
            status="failed",
            score=60,
            issues=[],
            summary="失败但没有问题",
            execution_time_ms=1,
            tokens_used=1,
        )


def test_review_result_rejects_warning_with_major_issue() -> None:
    reviewer = _build_reviewer("agent.style_checker", "文风检查员")

    with pytest.raises(ValidationError, match="warning review result"):
        ReviewResult(
            reviewer_id=reviewer.id,
            reviewer_name=reviewer.name,
            status="warning",
            score=70,
            issues=[
                ReviewIssue(
                    category="style_deviation",
                    severity="major",
                    description="主问题",
                )
            ],
            summary="warning 不能带 major",
            execution_time_ms=1,
            tokens_used=1,
        )


async def test_execute_review_resolves_reviewer_ids_from_config_loader() -> None:
    loader = ConfigLoader(CONFIG_ROOT)

    async def runner(content: str, reviewer: AgentConfig):
        assert content == "正文"
        return _passed_result(reviewer)

    executor = ReviewExecutor(runner, config_loader=loader)
    aggregated = await executor.execute_review(
        "正文",
        ["agent.style_checker"],
        "serial",
        ReviewConfig(pass_rule="all_pass"),
    )

    assert aggregated.results[0].reviewer_id == "agent.style_checker"
    assert aggregated.results[0].reviewer_name == "文风检查员"


def test_execute_review_requires_config_loader_for_reviewer_ids() -> None:
    async def runner(content: str, reviewer: AgentConfig):
        return _passed_result(reviewer)

    executor = ReviewExecutor(runner)

    with pytest.raises(
        ReviewExecutorError,
        match="config_loader is required",
    ):
        asyncio.run(
            executor.execute_review(
                "正文",
                ["agent.style_checker"],
                "serial",
                ReviewConfig(pass_rule="all_pass"),
            )
        )


def _build_reviewer(agent_id: str, name: str) -> AgentConfig:
    return AgentConfig.model_validate(
        {
            "id": agent_id,
            "name": name,
            "type": "reviewer",
            "system_prompt": "x",
            "skills": ["skill.review.style"],
        }
    )


def _passed_result(reviewer: AgentConfig) -> ReviewResult:
    return ReviewResult(
        reviewer_id=reviewer.id,
        reviewer_name=reviewer.name,
        status="passed",
        score=92,
        summary="通过",
        execution_time_ms=1,
        tokens_used=12,
    )


def _warning_result(reviewer: AgentConfig, description: str) -> ReviewResult:
    return ReviewResult(
        reviewer_id=reviewer.id,
        reviewer_name=reviewer.name,
        status="warning",
        score=75,
        issues=[
            ReviewIssue(
                category="style_deviation",
                severity="suggestion",
                description=description,
            )
        ],
        summary=description,
        execution_time_ms=1,
        tokens_used=8,
    )


def _failed_result(reviewer: AgentConfig, description: str, severity: str) -> ReviewResult:
    return ReviewResult(
        reviewer_id=reviewer.id,
        reviewer_name=reviewer.name,
        status="failed",
        score=45,
        issues=[
            ReviewIssue(
                category="style_deviation",
                severity=severity,
                description=description,
            )
        ],
        summary=description,
        execution_time_ms=1,
        tokens_used=16,
    )
