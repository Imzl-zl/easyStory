from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.credential.models import ModelCredential
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import (
    BudgetExceededError,
    BusinessRuleError,
    ConfigurationError,
    ModelFallbackExhaustedError,
)

from .snapshot_support import resolve_next_node_id
from .workflow_runtime_budget_support import (
    build_chapter_split_budget_outcome,
    build_completed_snapshot,
    ensure_chapter_split_budget_action_supported,
)
from .workflow_runtime_outcome_support import (
    build_failure_snapshot,
    build_model_fallback_node_outcome,
    resolve_review_pause_reason,
)
from .workflow_runtime_shared import NodeOutcome, ReviewCycleOutcome, WAITING_CONFIRM_TASK_STATUS


class WorkflowRuntimeExecuteMixin:
    async def _execute_chapter_split(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        execution = await self._create_node_execution(db, workflow, node)
        started_at = datetime.now(timezone.utc)
        budget_error: BudgetExceededError | None = None
        try:
            prompt_bundle, credential = await self._build_prompt_bundle(
                db,
                workflow,
                workflow_config,
                node,
                owner_id=owner_id,
                chapter_number=None,
            )
            execution.input_data = prompt_bundle["input_data"]
            await self._run_before_generate_hook(
                db,
                workflow,
                workflow_config,
                node,
                owner_id=owner_id,
                execution_id=execution.id,
            )
            try:
                raw_output = await self._call_llm(
                    db,
                    workflow,
                    workflow_config,
                    prompt_bundle,
                    owner_id=owner_id,
                    node_execution_id=execution.id,
                    usage_type="generate",
                    credential=credential,
                )
            except BudgetExceededError as exc:
                budget_error = exc
                raw_output = exc.raw_output
            except ModelFallbackExhaustedError as exc:
                self._fail_execution(db, execution, started_at, BusinessRuleError(exc.message))
                return build_model_fallback_node_outcome(
                    exc,
                    execution_id=execution.id,
                    next_node_id=node.id,
                    hook_payload={"node_id": node.id},
                )
            chapters = self._parse_chapter_split_output(raw_output["content"])
            if budget_error is not None:
                ensure_chapter_split_budget_action_supported(budget_error)
            await self._replace_chapter_tasks(db, workflow, chapters)
            self._append_artifact(
                db,
                execution,
                "chapter_tasks",
                {"chapters": [item.model_dump() for item in chapters]},
            )
            chapter_payload = self._chapter_split_hook_payload(chapters, budget_error)
            await self._run_after_generate_hook(
                db,
                workflow,
                workflow_config,
                node,
                owner_id=owner_id,
                execution_id=execution.id,
                extra=chapter_payload,
            )
            self._record_prompt_replay(db, execution, prompt_bundle, raw_output)
            self._complete_execution(db, execution, started_at, {"chapters_count": len(chapters)})
        except Exception as exc:
            self._fail_execution(db, execution, started_at, exc)
            raise
        next_node_id = resolve_next_node_id(workflow.workflow_snapshot or {}, current_node_id=node.id)
        completed_snapshot = build_completed_snapshot(self._completed_marker(execution))
        if budget_error is not None:
            return build_chapter_split_budget_outcome(
                completed_snapshot=completed_snapshot,
                next_node_id=next_node_id,
                budget_error=budget_error,
                node_execution_id=execution.id,
                hook_payload=chapter_payload,
            )
        return NodeOutcome(
            next_node_id=next_node_id,
            snapshot_extra=completed_snapshot,
            node_execution_id=execution.id,
            hook_payload=chapter_payload,
        )

    async def _execute_chapter_gen(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        task = await self._next_actionable_task(db, workflow)
        if task is None:
            return NodeOutcome(
                next_node_id=resolve_next_node_id(workflow.workflow_snapshot or {}, current_node_id=node.id)
            )
        await self._ensure_task_can_continue(db, task)
        execution = await self._create_node_execution(db, workflow, node)
        started_at = datetime.now(timezone.utc)
        try:
            prompt_bundle, credential, raw_output, generated_content, generation_budget_error = (
                await self._generate_chapter(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    task,
                    execution,
                    owner_id=owner_id,
                )
            )
            self._record_prompt_replay(db, execution, prompt_bundle, raw_output)
            review_outcome = await self._resolve_review_outcome(
                db,
                workflow,
                workflow_config,
                node,
                execution,
                generated_content,
                prompt_bundle=prompt_bundle,
                owner_id=owner_id,
                generation_budget_error=generation_budget_error,
            )
            candidate = await self._persist_chapter_candidate(
                db,
                workflow,
                task,
                prompt_bundle["context_snapshot_hash"],
                review_outcome,
            )
            hook_payload = self._chapter_generate_hook_payload(
                task,
                review_outcome,
                candidate,
                generated_content,
            )
            if candidate[0] is not None:
                await self._run_after_generate_hook(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    owner_id=owner_id,
                    execution_id=execution.id,
                    extra=hook_payload,
                )
            return self._finalize_chapter_execution(
                db,
                task,
                execution,
                started_at,
                review_outcome,
                candidate,
                hook_payload,
            )
        except ModelFallbackExhaustedError as exc:
            task.status = "failed"
            self._fail_execution(db, execution, started_at, BusinessRuleError(exc.message))
            return build_model_fallback_node_outcome(
                exc,
                execution_id=execution.id,
                next_node_id=execution.node_id,
                chapter_number=task.chapter_number,
                content_id=task.content_id,
                hook_payload={"chapter": {"number": task.chapter_number}},
            )
        except Exception as exc:
            task.status = "failed"
            self._fail_execution(db, execution, started_at, exc)
            raise

    async def _generate_chapter(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        task: ChapterTask,
        execution,
        *,
        owner_id: uuid.UUID,
    ) -> tuple[dict, ModelCredential, dict, str, BudgetExceededError | None]:
        prompt_bundle, credential = await self._build_prompt_bundle(
            db,
            workflow,
            workflow_config,
            node,
            owner_id=owner_id,
            chapter_number=task.chapter_number,
        )
        prompt_bundle["input_data"]["chapter_task_id"] = str(task.id)
        prompt_bundle["input_data"]["chapter_number"] = task.chapter_number
        execution.input_data = prompt_bundle["input_data"]
        await self._run_before_generate_hook(
            db,
            workflow,
            workflow_config,
            node,
            owner_id=owner_id,
            execution_id=execution.id,
            extra={"chapter": {"number": task.chapter_number, "task_id": str(task.id)}},
        )
        budget_error: BudgetExceededError | None = None
        try:
            raw_output = await self._call_llm(
                db,
                workflow,
                workflow_config,
                prompt_bundle,
                owner_id=owner_id,
                node_execution_id=execution.id,
                usage_type="generate",
                credential=credential,
            )
        except BudgetExceededError as exc:
            budget_error = exc
            raw_output = exc.raw_output
        content = raw_output.get("content")
        if not isinstance(content, str):
            raise ConfigurationError("Chapter generate output must be plain text")
        return prompt_bundle, credential, raw_output, content, budget_error

    def _finalize_chapter_execution(
        self,
        db: AsyncSession,
        task: ChapterTask,
        execution,
        started_at: datetime,
        review_outcome: ReviewCycleOutcome,
        candidate: tuple[str | None, str | None, int | None],
        hook_payload: dict[str, Any],
    ) -> NodeOutcome:
        content_id, version_id, word_count = candidate
        if version_id is not None:
            self._append_artifact(
                db,
                execution,
                "chapter_content",
                {"chapter_number": task.chapter_number, "content_id": str(content_id)},
                content_version_id=version_id,
                word_count=word_count,
            )
        if review_outcome.resolution == "passed":
            task.status = WAITING_CONFIRM_TASK_STATUS
            self._complete_execution(
                db,
                execution,
                started_at,
                {"chapter_number": task.chapter_number, "content_id": str(content_id)},
            )
            return NodeOutcome(
                next_node_id=execution.node_id,
                snapshot_extra=self._chapter_snapshot(execution, task),
                node_execution_id=execution.id,
                hook_payload=hook_payload,
            )
        if review_outcome.resolution == "skip":
            task.status = "skipped"
            self._skip_execution(
                db,
                execution,
                started_at,
                {"chapter_number": task.chapter_number, "status": "skipped"},
            )
            return NodeOutcome(
                next_node_id=execution.node_id,
                node_execution_id=execution.id,
                hook_payload=hook_payload,
            )
        if review_outcome.resolution == "pause":
            task.status = WAITING_CONFIRM_TASK_STATUS
            self._fail_execution(
                db,
                execution,
                started_at,
                BusinessRuleError(review_outcome.failure_message or "自动审核未通过"),
            )
            return NodeOutcome(
                next_node_id=execution.node_id,
                pause_reason=resolve_review_pause_reason(review_outcome),
                snapshot_extra=self._chapter_snapshot(execution, task),
                node_execution_id=execution.id,
                hook_payload=hook_payload,
            )
        task.status = "failed"
        self._fail_execution(
            db,
            execution,
            started_at,
            BusinessRuleError(review_outcome.failure_message or "自动精修失败"),
        )
        return NodeOutcome(
            next_node_id=execution.node_id,
            snapshot_extra=build_failure_snapshot(
                execution_id=execution.id,
                chapter_number=task.chapter_number,
                content_id=task.content_id,
            ),
            workflow_status="failed",
            node_execution_id=execution.id,
            hook_payload=hook_payload,
        )

    async def _run_before_generate_hook(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
        execution_id: uuid.UUID,
        extra: dict[str, Any] | None = None,
    ) -> None:
        context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "before_generate",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "before_generate",
                node_execution_id=execution_id,
                extra=extra,
            ),
            node_execution_id=execution_id,
        )
        await self._run_hook_event(context)

    async def _run_after_generate_hook(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
        execution_id: uuid.UUID,
        extra: dict[str, Any],
    ) -> None:
        context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "after_generate",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "after_generate",
                node_execution_id=execution_id,
                extra=extra,
            ),
            node_execution_id=execution_id,
        )
        await self._run_hook_event(context)

    def _chapter_split_hook_payload(
        self,
        chapters,
        budget_error: BudgetExceededError | None,
    ) -> dict[str, Any]:
        return {
            "chapters_count": len(chapters),
            "chapters": [item.model_dump(mode="json") for item in chapters],
            "budget_exceeded": budget_error is not None,
        }

    def _chapter_generate_hook_payload(
        self,
        task: ChapterTask,
        review_outcome: ReviewCycleOutcome,
        candidate: tuple[str | None, str | None, int | None],
        generated_content: str,
    ) -> dict[str, Any]:
        content_id, version_id, word_count = candidate
        return {
            "chapter": {
                "number": task.chapter_number,
                "title": task.title,
                "task_id": str(task.id),
            },
            "content": {
                "id": str(content_id) if content_id is not None else None,
                "version_id": str(version_id) if version_id is not None else None,
                "word_count": word_count,
                "text": review_outcome.final_content,
                "source": review_outcome.content_source,
                "generated_text": generated_content,
            },
            "review": {
                "resolution": review_outcome.resolution,
                "failure_message": review_outcome.failure_message,
                "pause_reason": review_outcome.pause_reason,
            },
        }
