from pathlib import Path

import pytest

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import AgentConfig, FixStrategy
from app.modules.review.engine import (
    AggregatedReviewResult,
    FixExecutionRequest,
    FixExecutor,
    FixExecutorError,
    FixPromptSource,
    ReviewExecutionFailure,
    ReviewIssue,
    ReviewResult,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


def test_determine_strategy_respects_explicit_selection_rule() -> None:
    executor = FixExecutor(_fix_runner_echo)
    aggregated = _aggregated_result(total_issues=10)

    assert (
        executor.determine_strategy(
            aggregated,
            FixStrategy(selection_rule="targeted", targeted_threshold=3, rewrite_threshold=6),
        )
        == "targeted"
    )
    assert (
        executor.determine_strategy(
            aggregated,
            FixStrategy(selection_rule="full_rewrite", targeted_threshold=3, rewrite_threshold=6),
        )
        == "full_rewrite"
    )


def test_determine_strategy_uses_auto_thresholds() -> None:
    executor = FixExecutor(_fix_runner_echo)

    targeted = executor.determine_strategy(
        _aggregated_result(total_issues=2),
        FixStrategy(selection_rule="auto", targeted_threshold=3, rewrite_threshold=6),
    )
    middle = executor.determine_strategy(
        _aggregated_result(total_issues=4),
        FixStrategy(selection_rule="auto", targeted_threshold=3, rewrite_threshold=6),
    )
    rewrite = executor.determine_strategy(
        _aggregated_result(total_issues=7),
        FixStrategy(selection_rule="auto", targeted_threshold=3, rewrite_threshold=6),
    )

    assert targeted == "targeted"
    assert middle == "targeted"
    assert rewrite == "full_rewrite"


def test_determine_strategy_rejects_invalid_thresholds() -> None:
    executor = FixExecutor(_fix_runner_echo)

    with pytest.raises(FixExecutorError, match="targeted_threshold"):
        executor.determine_strategy(
            _aggregated_result(total_issues=3),
            FixStrategy(selection_rule="auto", targeted_threshold=7, rewrite_threshold=6),
        )


def test_determine_strategy_rejects_execution_failures() -> None:
    executor = FixExecutor(_fix_runner_echo)

    with pytest.raises(FixExecutorError, match="execution_failures"):
        executor.determine_strategy(
            _aggregated_result(total_issues=0, execution_failures=1),
            FixStrategy(selection_rule="auto", targeted_threshold=3, rewrite_threshold=6),
        )


async def test_execute_fix_passes_request_to_runner() -> None:
    captured: list[FixExecutionRequest] = []
    loader = ConfigLoader(CONFIG_ROOT)

    async def runner(request: FixExecutionRequest) -> str:
        captured.append(request)
        return request.original_content + "\n[已精修]"

    executor = FixExecutor(runner, config_loader=loader)
    feedback = _aggregated_result(total_issues=2)
    prompt_source = executor.resolve_prompt_source(None, "skill.fix.xuanhuan")
    fixed = await executor.execute_fix(
        "原始正文",
        feedback,
        "targeted",
        prompt_source,
        original_prompt="原始提示词",
        fix_instructions="修正文风",
    )

    assert fixed.endswith("[已精修]")
    assert captured[0].strategy == "targeted"
    assert captured[0].prompt_source == FixPromptSource(source_type="skill", skill_id="skill.fix.xuanhuan")
    assert "问题统计" in captured[0].review_feedback
    assert captured[0].review_severity == "major"
    assert captured[0].original_prompt == "原始提示词"
    assert captured[0].fix_instructions == "修正文风"


def test_resolve_prompt_source_falls_back_to_builtin_prompt() -> None:
    executor = FixExecutor(_fix_runner_echo)

    prompt_source = executor.resolve_prompt_source(None, None)

    assert prompt_source.source_type == "builtin"
    assert "请根据审核反馈修改内容" in (prompt_source.prompt_template or "")


async def test_execute_fix_rejects_empty_output() -> None:
    async def runner(request: FixExecutionRequest) -> str:
        return "   "

    executor = FixExecutor(runner)

    with pytest.raises(FixExecutorError, match="empty content"):
        await executor.execute_fix(
            "原始正文",
            _aggregated_result(total_issues=1),
            "targeted",
            executor.resolve_prompt_source(None, None),
        )


async def test_execute_fix_rejects_invalid_prompt_source() -> None:
    executor = FixExecutor(_fix_runner_echo)

    with pytest.raises(FixExecutorError, match="skill prompt source"):
        await executor.execute_fix(
            "原始正文",
            _aggregated_result(total_issues=1),
            "targeted",
            FixPromptSource(source_type="skill"),
        )


async def test_execute_fix_rejects_execution_failures() -> None:
    executor = FixExecutor(_fix_runner_echo)

    with pytest.raises(FixExecutorError, match="execution_failures"):
        await executor.execute_fix(
            "原始正文",
            _aggregated_result(total_issues=0, execution_failures=1),
            "targeted",
            executor.resolve_prompt_source(None, None),
        )


def test_resolve_prompt_source_uses_node_then_workflow_default() -> None:
    executor = FixExecutor(_fix_runner_echo)

    assert executor.resolve_prompt_source("skill.fix.xuanhuan", None) == FixPromptSource(
        source_type="skill",
        skill_id="skill.fix.xuanhuan",
    )
    assert executor.resolve_prompt_source(None, "skill.fix.xuanhuan") == FixPromptSource(
        source_type="skill",
        skill_id="skill.fix.xuanhuan",
    )


async def _fix_runner_echo(request: FixExecutionRequest) -> str:
    return request.original_content


def _aggregated_result(
    total_issues: int,
    *,
    execution_failures: int = 0,
) -> AggregatedReviewResult:
    reviewer = AgentConfig.model_validate(
        {
            "id": "agent.style_checker",
            "name": "文风检查员",
            "type": "reviewer",
            "system_prompt": "x",
            "skills": ["skill.review.style"],
        }
    )
    issues = [
        ReviewIssue(
            category="style_deviation",
            severity="major",
            description=f"问题 {index}",
        )
        for index in range(total_issues)
    ]
    result = ReviewResult(
        reviewer_id=reviewer.id,
        reviewer_name=reviewer.name,
        status="failed" if issues else "passed",
        score=50 if issues else 95,
        issues=issues,
        summary="有问题" if issues else "通过",
        execution_time_ms=1,
        tokens_used=10,
    )
    return AggregatedReviewResult(
        overall_status="failed" if issues or execution_failures else "passed",
        results=[result],
        execution_failures=[
            ReviewExecutionFailure(
                reviewer_id=f"agent.execution_{index}",
                reviewer_name=f"执行失败 {index}",
                error_type="execution_error",
                message="Reviewer failed: boom",
                execution_time_ms=1,
            )
            for index in range(execution_failures)
        ],
        total_issues=total_issues,
        critical_count=0,
        major_count=total_issues,
        minor_count=0,
        pass_rule="no_critical",
    )
