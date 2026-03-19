from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Literal

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import FixStrategy
from app.shared.runtime.errors import EasyStoryError

from .contracts import AggregatedReviewResult

BUILTIN_FIX_PROMPT_TEMPLATE = "请根据审核反馈修改内容：\n{review_feedback}"
FixMode = Literal["targeted", "full_rewrite"]


@dataclass(frozen=True)
class FixPromptSource:
    source_type: Literal["skill", "builtin"]
    skill_id: str | None = None
    prompt_template: str | None = None


@dataclass(frozen=True)
class FixExecutionRequest:
    original_content: str
    review_feedback: str
    review_severity: str
    aggregated_result: AggregatedReviewResult
    strategy: FixMode
    prompt_source: FixPromptSource
    original_prompt: str | None = None
    fix_instructions: str | None = None


FixRunner = Callable[[FixExecutionRequest], Awaitable[str]]


class FixExecutorError(EasyStoryError):
    """Fix execution contract errors."""


class FixExecutor:
    def __init__(
        self,
        fix_runner: FixRunner,
        *,
        config_loader: ConfigLoader | None = None,
    ) -> None:
        self.fix_runner = fix_runner
        self.config_loader = config_loader

    def determine_strategy(
        self,
        aggregated_result: AggregatedReviewResult,
        config: FixStrategy,
    ) -> FixMode:
        self._validate_feedback_ready(aggregated_result)
        self._validate_thresholds(config)
        if config.selection_rule == "targeted":
            return "targeted"
        if config.selection_rule == "full_rewrite":
            return "full_rewrite"
        issue_count = self._issue_count(aggregated_result)
        if issue_count <= config.targeted_threshold:
            return "targeted"
        if issue_count > config.rewrite_threshold:
            return "full_rewrite"
        return "targeted"

    def resolve_prompt_source(
        self,
        node_fix_skill: str | None,
        workflow_fix_skill: str | None,
    ) -> FixPromptSource:
        skill_id = node_fix_skill or workflow_fix_skill
        if skill_id:
            self._validate_skill_id(skill_id)
            return FixPromptSource(source_type="skill", skill_id=skill_id)
        return FixPromptSource(
            source_type="builtin",
            prompt_template=BUILTIN_FIX_PROMPT_TEMPLATE,
        )

    async def execute_fix(
        self,
        original_content: str,
        feedback: AggregatedReviewResult,
        strategy: FixMode,
        prompt_source: FixPromptSource,
        *,
        original_prompt: str | None = None,
        fix_instructions: str | None = None,
    ) -> str:
        if strategy not in {"targeted", "full_rewrite"}:
            raise FixExecutorError(f"Unsupported fix strategy: {strategy}")
        self._validate_feedback_ready(feedback)
        self._validate_prompt_source(prompt_source)
        request = FixExecutionRequest(
            original_content=original_content,
            review_feedback=self._serialize_feedback(feedback),
            review_severity=self._max_severity(feedback),
            aggregated_result=feedback,
            strategy=strategy,
            prompt_source=prompt_source,
            original_prompt=original_prompt,
            fix_instructions=fix_instructions,
        )
        fixed_content = await self.fix_runner(request)
        if not fixed_content.strip():
            raise FixExecutorError("Fix runner returned empty content")
        return fixed_content

    def _validate_skill_id(self, skill_id: str) -> None:
        if self.config_loader is not None:
            self.config_loader.load_skill(skill_id)

    def _validate_prompt_source(self, prompt_source: FixPromptSource) -> None:
        if prompt_source.source_type == "skill" and not prompt_source.skill_id:
            raise FixExecutorError("skill prompt source requires skill_id")
        if prompt_source.source_type == "builtin" and not prompt_source.prompt_template:
            raise FixExecutorError("builtin prompt source requires prompt_template")

    def _validate_thresholds(self, config: FixStrategy) -> None:
        if config.targeted_threshold < 0 or config.rewrite_threshold < 0:
            raise FixExecutorError("Fix thresholds must be >= 0")
        if config.targeted_threshold > config.rewrite_threshold:
            raise FixExecutorError("targeted_threshold cannot exceed rewrite_threshold")

    def _validate_feedback_ready(self, aggregated_result: AggregatedReviewResult) -> None:
        if aggregated_result.execution_failures:
            raise FixExecutorError("Cannot execute fix when review execution_failures exist")

    def _issue_count(self, aggregated_result: AggregatedReviewResult) -> int:
        derived_count = sum(len(result.issues) for result in aggregated_result.results)
        return max(aggregated_result.total_issues, derived_count)

    def _serialize_feedback(self, aggregated_result: AggregatedReviewResult) -> str:
        lines = [
            f"整体结论：{aggregated_result.overall_status}",
            f"聚合规则：{aggregated_result.pass_rule}",
            f"问题统计：critical={aggregated_result.critical_count}, "
            f"major={aggregated_result.major_count}, minor={aggregated_result.minor_count}",
        ]
        for result in aggregated_result.results:
            lines.append(f"审核员：{result.reviewer_name}（{result.status}）")
            lines.append(f"摘要：{result.summary}")
            for index, issue in enumerate(result.issues, start=1):
                lines.append(
                    f"{index}. [{issue.severity}/{issue.category}] {issue.description}"
                )
        return "\n".join(lines)

    def _max_severity(self, aggregated_result: AggregatedReviewResult) -> str:
        if aggregated_result.critical_count > 0:
            return "critical"
        if aggregated_result.major_count > 0:
            return "major"
        if aggregated_result.minor_count > 0:
            return "minor"
        return "suggestion"
