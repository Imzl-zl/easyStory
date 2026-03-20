from __future__ import annotations

import asyncio
import uuid
from typing import Any, Sequence

from app.modules.config_registry.schemas.config_schemas import ModelConfig, NodeConfig, WorkflowConfig
from app.modules.review.engine import FixExecutionRequest, FixExecutor, ReviewExecutor
from app.modules.review.engine.contracts import AggregatedReviewResult
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import ConfigurationError

from .snapshot_support import load_agent_snapshot, load_skill_snapshot
from .workflow_runtime_shared import ReviewCycleOutcome


class WorkflowRuntimeReviewMixin:
    def _run_auto_review(
        self,
        db,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution: NodeExecution,
        content: str,
        *,
        prompt_bundle: dict[str, Any],
        owner_id: uuid.UUID,
    ) -> ReviewCycleOutcome:
        auto_review = node.auto_review if node.auto_review is not None else workflow_config.settings.auto_review
        if not auto_review:
            return ReviewCycleOutcome("passed", content, "generated")
        reviewers = [load_agent_snapshot(workflow.agents_snapshot or {}, item) for item in node.reviewers]
        aggregated = self._run_review_round(
            db, workflow, node, execution, content, reviewers, owner_id=owner_id, review_type="auto_review"
        )
        if aggregated.overall_status == "passed":
            return ReviewCycleOutcome("passed", content, "generated")
        if aggregated.execution_failures:
            return ReviewCycleOutcome("pause", content, "generated", failure_message="自动审核执行失败")
        auto_fix = node.auto_fix if node.auto_fix is not None else workflow_config.settings.auto_fix
        if not auto_fix:
            return ReviewCycleOutcome("pause", content, "generated", failure_message="自动审核未通过")
        return self._run_fix_cycle(
            db, workflow, workflow_config, node, execution, prompt_bundle, content, aggregated, reviewers, owner_id
        )

    def _run_review_round(
        self,
        db,
        workflow: WorkflowExecution,
        node: NodeConfig,
        execution: NodeExecution,
        content: str,
        reviewers: Sequence[Any],
        *,
        owner_id: uuid.UUID,
        review_type: str,
    ) -> AggregatedReviewResult:
        async def runner(text: str, reviewer):
            return await self._run_reviewer(db, workflow, reviewer, text, owner_id=owner_id)

        aggregated = asyncio.run(
            ReviewExecutor(runner).execute_review(
                content,
                reviewers,
                node.review_mode,
                node.review_config,
                max_concurrent_reviewers=node.max_concurrent_reviewers,
            )
        )
        self._append_review_actions(execution, aggregated, review_type)
        return aggregated

    def _append_review_actions(
        self,
        execution: NodeExecution,
        aggregated: AggregatedReviewResult,
        review_type: str,
    ) -> None:
        for result in aggregated.results:
            execution.review_actions.append(
                ReviewAction(
                    agent_id=result.reviewer_id,
                    reviewer_name=result.reviewer_name,
                    review_type=review_type,
                    status=result.status,
                    score=result.score,
                    summary=result.summary,
                    issues=[item.model_dump(mode="json") for item in result.issues],
                    execution_time_ms=result.execution_time_ms,
                    tokens_used=result.tokens_used,
                )
            )
        for failure in aggregated.execution_failures:
            execution.review_actions.append(
                ReviewAction(
                    agent_id=failure.reviewer_id,
                    reviewer_name=failure.reviewer_name,
                    review_type=review_type,
                    status="failed",
                    summary=failure.message,
                    execution_time_ms=failure.execution_time_ms,
                )
            )

    def _run_fix_cycle(
        self,
        db,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution: NodeExecution,
        prompt_bundle: dict[str, Any],
        content: str,
        aggregated: AggregatedReviewResult,
        reviewers: Sequence[Any],
        owner_id: uuid.UUID,
    ) -> ReviewCycleOutcome:
        current_content = content
        max_fix_attempts = self._resolve_max_fix_attempts(node, workflow_config)
        for attempt in range(1, max_fix_attempts + 1):
            current_content = self._run_fix_attempt(
                db, workflow, workflow_config, node, execution, prompt_bundle, current_content, aggregated, owner_id
            )
            re_reviewers = self._select_re_reviewers(reviewers, aggregated, node.review_config.re_review_scope)
            aggregated = self._run_review_round(
                db,
                workflow,
                node,
                execution,
                current_content,
                re_reviewers,
                owner_id=owner_id,
                review_type=f"auto_re_review_{attempt}",
            )
            if aggregated.overall_status == "passed":
                return ReviewCycleOutcome("passed", current_content, "auto_fix")
            if aggregated.execution_failures:
                return ReviewCycleOutcome("pause", current_content, "auto_fix", failure_message="自动复审执行失败")
        return self._resolve_fix_failure(node, current_content)

    def _run_fix_attempt(
        self,
        db,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution: NodeExecution,
        prompt_bundle: dict[str, Any],
        content: str,
        aggregated: AggregatedReviewResult,
        owner_id: uuid.UUID,
    ) -> str:
        recorded_prompt_bundle: dict[str, Any] = {}
        recorded_raw_output: dict[str, Any] = {}

        async def runner(request: FixExecutionRequest) -> str:
            nonlocal recorded_prompt_bundle, recorded_raw_output
            recorded_prompt_bundle = self._build_fix_prompt_bundle(workflow, request, prompt_bundle["model"])
            recorded_raw_output = await self._call_llm(
                db,
                workflow,
                recorded_prompt_bundle,
                owner_id=owner_id,
            )
            content = recorded_raw_output.get("content")
            if not isinstance(content, str):
                raise ConfigurationError("Fix LLM output must be plain text")
            return content

        executor = FixExecutor(runner)
        strategy = executor.determine_strategy(aggregated, node.fix_strategy)
        prompt_source = executor.resolve_prompt_source(node.fix_skill, workflow_config.settings.default_fix_skill)
        fixed_content = asyncio.run(
            executor.execute_fix(
                content, aggregated, strategy, prompt_source, original_prompt=prompt_bundle["prompt"]
            )
        )
        self._record_prompt_replay(db, execution, recorded_prompt_bundle, recorded_raw_output, replay_type="fix")
        return fixed_content

    def _build_fix_prompt_bundle(
        self,
        workflow: WorkflowExecution,
        request: FixExecutionRequest,
        fallback_model: ModelConfig,
    ) -> dict[str, Any]:
        prompt_source = request.prompt_source
        prompt_variables = {
            "original_content": request.original_content,
            "review_feedback": request.review_feedback,
            "review_severity": request.review_severity,
            "original_prompt": request.original_prompt or "",
            "fix_instructions": request.fix_instructions or "",
        }
        if prompt_source.source_type == "skill":
            skill = load_skill_snapshot(workflow.skills_snapshot or {}, prompt_source.skill_id)
            prompt = self.template_renderer.render(skill.prompt, prompt_variables)
            model = skill.model or fallback_model
        else:
            prompt = self.template_renderer.render(prompt_source.prompt_template or "", prompt_variables)
            model = fallback_model
        self._validate_fix_model(model)
        return {"prompt": prompt, "system_prompt": None, "model": model, "response_format": "text"}

    def _validate_fix_model(self, model: ModelConfig | None) -> None:
        if model is None or not model.name or not model.provider:
            raise ConfigurationError("Fix runtime is missing executable model configuration")

    def _resolve_max_fix_attempts(self, node: NodeConfig, workflow_config: WorkflowConfig) -> int:
        max_fix_attempts = (
            node.max_fix_attempts
            if node.max_fix_attempts is not None
            else workflow_config.safety.max_fix_attempts
        )
        if max_fix_attempts < 1:
            raise ConfigurationError("max_fix_attempts must be >= 1")
        return max_fix_attempts

    def _select_re_reviewers(
        self,
        reviewers: Sequence[Any],
        aggregated: AggregatedReviewResult,
        scope: str,
    ) -> list[Any]:
        if scope == "all":
            return list(reviewers)
        if scope != "failed_only":
            raise ConfigurationError(f"Unsupported re_review_scope: {scope}")
        failed_ids = {result.reviewer_id for result in aggregated.results if result.status != "passed"}
        return [reviewer for reviewer in reviewers if reviewer.id in failed_ids] or list(reviewers)

    def _resolve_fix_failure(self, node: NodeConfig, content: str) -> ReviewCycleOutcome:
        message = "自动精修达到最大次数，仍未通过审核"
        if node.on_fix_fail == "skip":
            return ReviewCycleOutcome("skip", content, "auto_fix", failure_message=message)
        if node.on_fix_fail == "fail":
            return ReviewCycleOutcome("fail", content, "auto_fix", failure_message=message)
        return ReviewCycleOutcome("pause", content, "auto_fix", failure_message=message)

    async def _run_reviewer(
        self,
        db,
        workflow: WorkflowExecution,
        reviewer,
        content: str,
        *,
        owner_id: uuid.UUID,
    ) -> Any:
        if not reviewer.skills:
            raise ConfigurationError(f"Reviewer {reviewer.id} has no skills configured")
        skill = load_skill_snapshot(workflow.skills_snapshot or {}, reviewer.skills[0])
        prompt = self.template_renderer.render(skill.prompt, {"content": content})
        model = reviewer.model or skill.model
        if model is None or not model.name or not model.provider:
            raise ConfigurationError(f"Reviewer {reviewer.id} is missing model configuration")
        raw_output = await self._call_llm(
            db,
            workflow,
            {
                "prompt": prompt,
                "system_prompt": reviewer.system_prompt,
                "model": model,
                "response_format": "json_object",
            },
            owner_id=owner_id,
        )
        return self._parse_json(raw_output["content"])
