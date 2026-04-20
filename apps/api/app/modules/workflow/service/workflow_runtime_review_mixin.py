from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.review.engine import ReviewExecutor
from app.modules.review.engine.contracts import AggregatedReviewResult
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import BudgetExceededError, ConfigurationError, ModelFallbackExhaustedError

from .snapshot_support import load_agent_snapshot, load_skill_snapshot
from .workflow_review_fix_runtime import LangGraphWorkflowReviewFixRuntime
from .workflow_runtime_budget_support import build_budget_review_outcome
from .workflow_runtime_shared import ReviewCycleOutcome


class WorkflowRuntimeReviewMixin:
    async def _resolve_review_outcome(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution: NodeExecution,
        generated_content: str,
        *,
        prompt_bundle: dict[str, Any],
        owner_id: uuid.UUID,
        generation_budget_error: BudgetExceededError | None,
    ) -> ReviewCycleOutcome:
        runtime = LangGraphWorkflowReviewFixRuntime(
            generated_content=generated_content,
            generation_budget_error=generation_budget_error,
            build_budget_review_outcome=lambda budget_error, content: build_budget_review_outcome(
                budget_error,
                generated_content=content,
            ),
            resolve_auto_review_enabled=lambda: (
                node.auto_review
                if node.auto_review is not None
                else workflow_config.settings.auto_review
            ),
            load_reviewers=lambda: [
                load_agent_snapshot(workflow.agents_snapshot or {}, item)
                for item in node.reviewers
            ],
            run_review_round=lambda content, reviewers, review_type: self._run_review_round(
                db,
                workflow,
                workflow_config,
                node,
                execution,
                content,
                reviewers,
                owner_id=owner_id,
                review_type=review_type,
            ),
            resolve_auto_fix_enabled=lambda: (
                node.auto_fix if node.auto_fix is not None else workflow_config.settings.auto_fix
            ),
            run_fix_attempt=lambda content, aggregated, attempt, max_attempts: self._run_fix_attempt(
                db,
                workflow,
                workflow_config,
                node,
                execution,
                prompt_bundle,
                content,
                aggregated,
                owner_id,
                attempt=attempt,
                max_attempts=max_attempts,
            ),
            resolve_max_fix_attempts=lambda: self._resolve_max_fix_attempts(node, workflow_config),
            select_re_reviewers=lambda reviewers, aggregated: self._select_re_reviewers(
                reviewers,
                aggregated,
                node.review_config.re_review_scope,
            ),
            resolve_fix_failure=lambda content: self._resolve_fix_failure(node, content),
            resolve_model_fallback_review_outcome=lambda exc, content, content_source: (
                self._resolve_model_fallback_review_outcome(
                    exc,
                    content=content,
                    content_source=content_source,
                )
            ),
        )
        return await runtime.run()

    async def _run_review_round(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution: NodeExecution,
        content: str,
        reviewers: Sequence[Any],
        *,
        owner_id: uuid.UUID,
        review_type: str,
    ) -> AggregatedReviewResult:
        await self._run_before_review_hook(
            db,
            workflow,
            workflow_config,
            node,
            execution.id,
            owner_id=owner_id,
            content=content,
            reviewers=reviewers,
            review_type=review_type,
        )

        async def runner(text: str, reviewer):
            return await self._run_reviewer(
                db,
                workflow,
                workflow_config,
                execution,
                reviewer,
                text,
                owner_id=owner_id,
            )

        try:
            aggregated = await ReviewExecutor(runner).execute_review(
                content,
                reviewers,
                node.review_mode,
                node.review_config,
                max_concurrent_reviewers=node.max_concurrent_reviewers,
            )
        except BudgetExceededError as exc:
            partial = exc.partial_aggregated_review
            if partial is not None:
                self._append_review_actions(db, execution, partial, review_type)
            raise
        self._append_review_actions(db, execution, aggregated, review_type)
        await self._run_after_review_hooks(
            db,
            workflow,
            workflow_config,
            node,
            execution.id,
            owner_id=owner_id,
            content=content,
            aggregated=aggregated,
            review_type=review_type,
        )
        return aggregated

    def _append_review_actions(
        self,
        db: AsyncSession,
        execution: NodeExecution,
        aggregated: AggregatedReviewResult,
        review_type: str,
    ) -> None:
        for result in aggregated.results:
            db.add(
                ReviewAction(
                    node_execution_id=execution.id,
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
            db.add(
                ReviewAction(
                    node_execution_id=execution.id,
                    agent_id=failure.reviewer_id,
                    reviewer_name=failure.reviewer_name,
                    review_type=review_type,
                    status="failed",
                    summary=failure.message,
                    execution_time_ms=failure.execution_time_ms,
                )
            )

    async def _run_reviewer(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        execution: NodeExecution,
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
        if model is None or not model.provider:
            raise ConfigurationError(f"Reviewer {reviewer.id} is missing model configuration")
        raw_output = await self._call_llm(
            db,
            workflow,
            workflow_config,
            {
                "prompt": prompt,
                "system_prompt": reviewer.system_prompt,
                "model": model,
                "response_format": "json_object",
            },
            owner_id=owner_id,
            node_execution_id=execution.id,
            usage_type="review",
        )
        return self._parse_json(raw_output["content"])

    def _resolve_model_fallback_review_outcome(
        self,
        exc: ModelFallbackExhaustedError,
        *,
        content: str,
        content_source: str,
    ) -> ReviewCycleOutcome:
        if exc.action == "fail":
            return ReviewCycleOutcome("fail", content, content_source, failure_message=exc.message)
        return ReviewCycleOutcome(
            "pause",
            content,
            content_source,
            failure_message=exc.message,
            pause_reason="model_fallback_exhausted",
        )

    async def _run_before_review_hook(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution_id,
        *,
        owner_id: uuid.UUID,
        content: str,
        reviewers: Sequence[Any],
        review_type: str,
    ) -> None:
        context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "before_review",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "before_review",
                node_execution_id=execution_id,
                extra=self._review_hook_payload(content, reviewers, review_type),
            ),
            node_execution_id=execution_id,
        )
        await self._run_hook_event(context)

    async def _run_after_review_hooks(
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
        review_type: str,
    ) -> None:
        extra = self._review_result_payload(content, aggregated, review_type)
        context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "after_review",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "after_review",
                node_execution_id=execution_id,
                extra=extra,
            ),
            node_execution_id=execution_id,
        )
        await self._run_hook_event(context)
        if aggregated.overall_status == "passed" and not aggregated.execution_failures:
            return
        failure_context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "on_review_fail",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "on_review_fail",
                node_execution_id=execution_id,
                extra=extra,
            ),
            node_execution_id=execution_id,
        )
        await self._run_hook_event(failure_context)

    def _review_hook_payload(
        self,
        content: str,
        reviewers: Sequence[Any],
        review_type: str,
    ) -> dict[str, Any]:
        return {
            "review_type": review_type,
            "content": content,
            "reviewer_ids": [reviewer.id for reviewer in reviewers],
            "reviewer_names": [reviewer.name for reviewer in reviewers],
        }

    def _review_result_payload(
        self,
        content: str,
        aggregated: AggregatedReviewResult,
        review_type: str,
    ) -> dict[str, Any]:
        return {
            "review_type": review_type,
            "content": content,
            "aggregated_review": aggregated.model_dump(mode="json"),
        }
