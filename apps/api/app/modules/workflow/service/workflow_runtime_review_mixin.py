from __future__ import annotations

import asyncio
from typing import Any
import uuid

from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.review.engine import ReviewExecutor
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import ConfigurationError

from .snapshot_support import load_agent_snapshot, load_skill_snapshot


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
        owner_id: uuid.UUID,
    ) -> str:
        auto_review = node.auto_review if node.auto_review is not None else workflow_config.settings.auto_review
        if not auto_review:
            return "passed"
        reviewers = [load_agent_snapshot(workflow.agents_snapshot or {}, item) for item in node.reviewers]

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
        for result in aggregated.results:
            execution.review_actions.append(
                ReviewAction(
                    agent_id=result.reviewer_id,
                    reviewer_name=result.reviewer_name,
                    review_type="auto_review",
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
                    review_type="auto_review",
                    status="failed",
                    summary=failure.message,
                    execution_time_ms=failure.execution_time_ms,
                )
            )
        if aggregated.overall_status == "failed":
            auto_fix = node.auto_fix if node.auto_fix is not None else workflow_config.settings.auto_fix
            if auto_fix:
                raise ConfigurationError("auto_fix runtime is not implemented yet")
            return "failed"
        return "passed"

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
