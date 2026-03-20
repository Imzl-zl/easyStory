from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import uuid

from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import BudgetExceededError, BusinessRuleError, ConfigurationError

from .snapshot_support import resolve_next_node_id
from .workflow_runtime_budget_support import (
    build_budget_review_outcome,
    build_chapter_split_budget_outcome,
    build_completed_snapshot,
    ensure_chapter_split_budget_action_supported,
)
from .workflow_runtime_shared import NodeOutcome, ReviewCycleOutcome, WAITING_CONFIRM_TASK_STATUS


class WorkflowRuntimeExecuteMixin:
    def _execute_chapter_split(
        self,
        db,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        execution = self._create_node_execution(db, workflow, node)
        started_at = datetime.now(timezone.utc)
        budget_error: BudgetExceededError | None = None
        try:
            prompt_bundle = self._build_prompt_bundle(
                db, workflow, workflow_config, node, chapter_number=None
            )
            execution.input_data = prompt_bundle["input_data"]
            try:
                raw_output = asyncio.run(
                    self._call_llm(
                        db,
                        workflow,
                        workflow_config,
                        prompt_bundle,
                        owner_id=owner_id,
                        node_execution_id=execution.id,
                        usage_type="generate",
                    )
                )
            except BudgetExceededError as exc:
                budget_error = exc
                raw_output = exc.raw_output
            chapters = self._parse_chapter_split_output(raw_output["content"])
            if budget_error is not None:
                ensure_chapter_split_budget_action_supported(budget_error)
            self._replace_chapter_tasks(db, workflow, chapters)
            self._append_artifact(
                execution, "chapter_tasks", {"chapters": [item.model_dump() for item in chapters]}
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
            )
        return NodeOutcome(next_node_id=next_node_id, snapshot_extra=completed_snapshot)

    def _execute_chapter_gen(
        self,
        db,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        task = self._next_actionable_task(db, workflow)
        if task is None:
            return NodeOutcome(
                next_node_id=resolve_next_node_id(workflow.workflow_snapshot or {}, current_node_id=node.id)
            )
        self._ensure_task_can_continue(db, task)
        execution = self._create_node_execution(db, workflow, node)
        started_at = datetime.now(timezone.utc)
        try:
            prompt_bundle, raw_output, generated_content, generation_budget_error = self._generate_chapter(
                db, workflow, workflow_config, node, task, execution, owner_id=owner_id
            )
            self._record_prompt_replay(db, execution, prompt_bundle, raw_output)
            review_outcome = self._resolve_review_outcome(
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
            candidate = self._persist_chapter_candidate(
                db, workflow, task, prompt_bundle["context_snapshot_hash"], review_outcome
            )
            return self._finalize_chapter_execution(
                db, task, execution, started_at, review_outcome, candidate
            )
        except Exception as exc:
            task.status = "failed"
            self._fail_execution(db, execution, started_at, exc)
            raise

    def _generate_chapter(
        self,
        db,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        task: ChapterTask,
        execution,
        *,
        owner_id: uuid.UUID,
    ) -> tuple[dict, dict, str, BudgetExceededError | None]:
        prompt_bundle = self._build_prompt_bundle(
            db, workflow, workflow_config, node, chapter_number=task.chapter_number
        )
        prompt_bundle["input_data"]["chapter_task_id"] = str(task.id)
        prompt_bundle["input_data"]["chapter_number"] = task.chapter_number
        execution.input_data = prompt_bundle["input_data"]
        budget_error: BudgetExceededError | None = None
        try:
            raw_output = asyncio.run(
                self._call_llm(
                    db,
                    workflow,
                    workflow_config,
                    prompt_bundle,
                    owner_id=owner_id,
                    node_execution_id=execution.id,
                    usage_type="generate",
                )
            )
        except BudgetExceededError as exc:
            budget_error = exc
            raw_output = exc.raw_output
        content = raw_output.get("content")
        if not isinstance(content, str):
            raise ConfigurationError("Chapter generate output must be plain text")
        return prompt_bundle, raw_output, content, budget_error

    def _resolve_review_outcome(
        self,
        db,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        execution,
        generated_content: str,
        *,
        prompt_bundle: dict,
        owner_id: uuid.UUID,
        generation_budget_error: BudgetExceededError | None,
    ) -> ReviewCycleOutcome:
        if generation_budget_error is not None:
            return build_budget_review_outcome(
                generation_budget_error,
                generated_content=generated_content,
            )
        try:
            return self._run_auto_review(
                db,
                workflow,
                workflow_config,
                node,
                execution,
                generated_content,
                prompt_bundle=prompt_bundle,
                owner_id=owner_id,
            )
        except BudgetExceededError as exc:
            return build_budget_review_outcome(exc, generated_content=generated_content)

    def _finalize_chapter_execution(
        self,
        db,
        task: ChapterTask,
        execution,
        started_at: datetime,
        review_outcome: ReviewCycleOutcome,
        candidate: tuple[str | None, str | None, int | None],
    ) -> NodeOutcome:
        content_id, version_id, word_count = candidate
        if version_id is not None:
            self._append_artifact(
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
            return NodeOutcome(next_node_id=execution.node_id, snapshot_extra=self._chapter_snapshot(execution, task))
        if review_outcome.resolution == "skip":
            task.status = "skipped"
            self._skip_execution(
                db,
                execution, started_at, {"chapter_number": task.chapter_number, "status": "skipped"}
            )
            return NodeOutcome(next_node_id=execution.node_id)
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
                pause_reason=self._pause_reason(review_outcome),
                snapshot_extra=self._chapter_snapshot(execution, task),
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
            snapshot_extra=self._failure_snapshot(execution, task),
            workflow_status="failed",
        )

    def _pause_reason(self, review_outcome: ReviewCycleOutcome) -> str:
        if review_outcome.pause_reason is not None:
            return review_outcome.pause_reason
        return "review_failed"

    def _failure_snapshot(self, execution, task: ChapterTask) -> dict[str, str | int | None]:
        return {
            "current_node_execution_id": str(execution.id),
            "current_chapter_number": task.chapter_number,
            "content_id": str(task.content_id) if task.content_id is not None else None,
        }
