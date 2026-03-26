from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import ModelConfig, NodeConfig, WorkflowConfig
from app.modules.review.engine import FixExecutionRequest, FixExecutor
from app.modules.review.engine.contracts import AggregatedReviewResult
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import BudgetExceededError, ConfigurationError, ModelFallbackExhaustedError

from .snapshot_support import load_skill_snapshot
from .workflow_runtime_shared import ReviewCycleOutcome


class WorkflowRuntimeFixMixin:
    async def _run_fix_cycle(
        self,
        db: AsyncSession,
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
        content_source = "generated"
        max_fix_attempts = self._resolve_max_fix_attempts(node, workflow_config)
        for attempt in range(1, max_fix_attempts + 1):
            try:
                current_content = await self._run_fix_attempt(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    execution,
                    prompt_bundle,
                    current_content,
                    aggregated,
                    owner_id,
                    attempt=attempt,
                    max_attempts=max_fix_attempts,
                )
            except ModelFallbackExhaustedError as exc:
                return self._resolve_model_fallback_review_outcome(
                    exc,
                    content=current_content,
                    content_source=content_source,
                )
            content_source = "auto_fix"
            re_reviewers = self._select_re_reviewers(
                reviewers,
                aggregated,
                node.review_config.re_review_scope,
            )
            try:
                aggregated = await self._run_review_round(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    execution,
                    current_content,
                    re_reviewers,
                    owner_id=owner_id,
                    review_type=f"auto_re_review_{attempt}",
                )
            except ModelFallbackExhaustedError as exc:
                return self._resolve_model_fallback_review_outcome(
                    exc,
                    content=current_content,
                    content_source=content_source,
                )
            if aggregated.overall_status == "passed":
                return ReviewCycleOutcome("passed", current_content, "auto_fix")
            if aggregated.execution_failures:
                return ReviewCycleOutcome("pause", current_content, "auto_fix", failure_message="自动复审执行失败")
        return self._resolve_fix_failure(node, current_content)

    async def _run_fix_attempt(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution: NodeExecution,
        prompt_bundle: dict[str, Any],
        content: str,
        aggregated: AggregatedReviewResult,
        owner_id: uuid.UUID,
        *,
        attempt: int,
        max_attempts: int,
    ) -> str:
        recorded_prompt_bundle: dict[str, Any] = {}
        recorded_raw_output: dict[str, Any] = {}
        await self._run_before_fix_hook(
            db,
            workflow,
            workflow_config,
            node,
            execution.id,
            owner_id=owner_id,
            content=content,
            aggregated=aggregated,
            attempt=attempt,
            max_attempts=max_attempts,
        )

        async def runner(request: FixExecutionRequest) -> str:
            nonlocal recorded_prompt_bundle, recorded_raw_output
            recorded_prompt_bundle = self._build_fix_prompt_bundle(workflow, request, prompt_bundle["model"])
            recorded_raw_output = await self._call_llm(
                db,
                workflow,
                workflow_config,
                recorded_prompt_bundle,
                owner_id=owner_id,
                node_execution_id=execution.id,
                usage_type="fix",
            )
            resolved_content = recorded_raw_output.get("content")
            if not isinstance(resolved_content, str):
                raise ConfigurationError("Fix LLM output must be plain text")
            return resolved_content

        executor = FixExecutor(runner)
        strategy = executor.determine_strategy(aggregated, node.fix_strategy)
        prompt_source = executor.resolve_prompt_source(node.fix_skill, workflow_config.settings.default_fix_skill)
        try:
            fixed_content = await executor.execute_fix(
                content,
                aggregated,
                strategy,
                prompt_source,
                original_prompt=prompt_bundle["prompt"],
            )
        except BudgetExceededError as exc:
            self._record_prompt_replay(
                db,
                execution,
                recorded_prompt_bundle,
                exc.raw_output,
                replay_type="fix",
            )
            raise
        self._record_prompt_replay(db, execution, recorded_prompt_bundle, recorded_raw_output, replay_type="fix")
        await self._run_after_fix_hook(
            db,
            workflow,
            workflow_config,
            node,
            execution.id,
            owner_id=owner_id,
            content=content,
            fixed_content=fixed_content,
            aggregated=aggregated,
            attempt=attempt,
            max_attempts=max_attempts,
        )
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
        if model is None or not model.provider:
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

    async def _run_before_fix_hook(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution_id,
        *,
        owner_id: uuid.UUID,
        content: str,
        aggregated: AggregatedReviewResult,
        attempt: int,
        max_attempts: int,
    ) -> None:
        context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "before_fix",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "before_fix",
                node_execution_id=execution_id,
                extra=self._fix_hook_payload(content, aggregated, attempt, max_attempts),
            ),
            node_execution_id=execution_id,
        )
        await self._run_hook_event(context)

    async def _run_after_fix_hook(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution_id,
        *,
        owner_id: uuid.UUID,
        content: str,
        fixed_content: str,
        aggregated: AggregatedReviewResult,
        attempt: int,
        max_attempts: int,
    ) -> None:
        extra = self._fix_hook_payload(content, aggregated, attempt, max_attempts)
        extra["fixed_content"] = fixed_content
        context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "after_fix",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "after_fix",
                node_execution_id=execution_id,
                extra=extra,
            ),
            node_execution_id=execution_id,
        )
        await self._run_hook_event(context)

    def _fix_hook_payload(
        self,
        content: str,
        aggregated: AggregatedReviewResult,
        attempt: int,
        max_attempts: int,
    ) -> dict[str, Any]:
        return {
            "attempt": attempt,
            "max_attempts": max_attempts,
            "content": content,
            "aggregated_review": aggregated.model_dump(mode="json"),
        }
