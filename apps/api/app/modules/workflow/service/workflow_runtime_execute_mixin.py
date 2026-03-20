from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import uuid

from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .snapshot_support import resolve_next_node_id
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
        try:
            prompt_bundle = self._build_prompt_bundle(
                db, workflow, workflow_config, node, chapter_number=None
            )
            execution.input_data = prompt_bundle["input_data"]
            raw_output = asyncio.run(self._call_llm(db, workflow, prompt_bundle, owner_id=owner_id))
            chapters = self._parse_chapter_split_output(raw_output["content"])
            self._replace_chapter_tasks(db, workflow, chapters)
            self._append_artifact(
                execution, "chapter_tasks", {"chapters": [item.model_dump() for item in chapters]}
            )
            self._record_prompt_replay(db, execution, prompt_bundle, raw_output)
            self._complete_execution(db, execution, started_at, {"chapters_count": len(chapters)})
        except Exception as exc:
            self._fail_execution(db, execution, started_at, exc)
            raise
        return NodeOutcome(
            next_node_id=resolve_next_node_id(workflow.workflow_snapshot or {}, current_node_id=node.id),
            snapshot_extra={"completed_nodes": [self._completed_marker(execution)]},
        )

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
            prompt_bundle, raw_output, generated_content = self._generate_chapter(
                db, workflow, workflow_config, node, task, execution, owner_id=owner_id
            )
            self._record_prompt_replay(db, execution, prompt_bundle, raw_output)
            review_outcome = self._run_auto_review(
                db,
                workflow,
                workflow_config,
                node,
                execution,
                generated_content,
                prompt_bundle=prompt_bundle,
                owner_id=owner_id,
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
    ) -> tuple[dict, dict, str]:
        prompt_bundle = self._build_prompt_bundle(
            db, workflow, workflow_config, node, chapter_number=task.chapter_number
        )
        prompt_bundle["input_data"]["chapter_task_id"] = str(task.id)
        prompt_bundle["input_data"]["chapter_number"] = task.chapter_number
        execution.input_data = prompt_bundle["input_data"]
        raw_output = asyncio.run(self._call_llm(db, workflow, prompt_bundle, owner_id=owner_id))
        content = raw_output.get("content")
        if not isinstance(content, str):
            raise ConfigurationError("Chapter generate output must be plain text")
        return prompt_bundle, raw_output, content

    def _persist_chapter_candidate(
        self,
        db,
        workflow: WorkflowExecution,
        task: ChapterTask,
        context_snapshot_hash: str,
        review_outcome: ReviewCycleOutcome,
    ) -> tuple[uuid.UUID | None, uuid.UUID | None, int | None]:
        if review_outcome.resolution == "skip":
            return None, None, None
        content, version = self._save_review_candidate(
            db,
            workflow.project_id,
            task.chapter_number,
            task.title,
            review_outcome,
            context_snapshot_hash,
        )
        task.content_id = content.id
        return content.id, version.id, version.word_count

    def _save_review_candidate(
        self,
        db,
        project_id,
        chapter_number: int,
        title: str,
        review_outcome: ReviewCycleOutcome,
        context_snapshot_hash: str,
    ):
        if review_outcome.content_source == "generated":
            return self.chapter_content_service.save_generated_draft(
                db,
                project_id,
                chapter_number,
                title=title,
                content_text=review_outcome.final_content,
                context_snapshot_hash=context_snapshot_hash,
            )
        return self.chapter_content_service.save_auto_fix_draft(
            db,
            project_id,
            chapter_number,
            title=title,
            content_text=review_outcome.final_content,
            context_snapshot_hash=context_snapshot_hash,
            change_summary=self._auto_fix_change_summary(review_outcome),
        )

    def _auto_fix_change_summary(self, review_outcome: ReviewCycleOutcome) -> str:
        if review_outcome.resolution == "passed":
            return "自动精修后通过复审"
        return "自动精修最终候选"

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
        return "review_failed"

    def _failure_snapshot(self, execution, task: ChapterTask) -> dict[str, str | int | None]:
        return {
            "current_node_execution_id": str(execution.id),
            "current_chapter_number": task.chapter_number,
            "content_id": str(task.content_id) if task.content_id is not None else None,
        }

    def _execute_export(
        self,
        db,
        workflow: WorkflowExecution,
        node: NodeConfig,
    ) -> NodeOutcome:
        execution = self._create_node_execution(db, workflow, node)
        started_at = datetime.now(timezone.utc)
        try:
            exports = self.export_service.export_workflow(
                db, workflow, formats=list(node.formats), config_snapshot=workflow.workflow_snapshot
            )
            self._append_artifact(execution, "export", {"export_ids": [str(item.id) for item in exports]})
            self._complete_execution(
                db,
                execution, started_at, {"export_ids": [str(item.id) for item in exports]}
            )
        except Exception as exc:
            self._fail_execution(db, execution, started_at, exc)
            raise
        return NodeOutcome(next_node_id=None)
