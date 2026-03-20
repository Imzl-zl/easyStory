from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import uuid
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.content.service import ChapterContentService
from app.modules.credential.service import CredentialService
from app.modules.export.service import ExportService
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime import SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm_tool_provider import LLM_GENERATE_TOOL

from .snapshot_support import (
    build_runtime_snapshot,
    load_workflow_snapshot,
    resolve_next_node_id,
    resolve_node_config,
)
from .workflow_runtime_persistence_mixin import WorkflowRuntimePersistenceMixin
from .workflow_runtime_prompt_mixin import WorkflowRuntimePromptMixin
from .workflow_runtime_review_mixin import WorkflowRuntimeReviewMixin
from .workflow_runtime_shared import NodeOutcome, WAITING_CONFIRM_TASK_STATUS
from .workflow_runtime_task_mixin import WorkflowRuntimeTaskMixin
from .workflow_service import WorkflowService


class WorkflowRuntimeService(
    WorkflowRuntimeTaskMixin,
    WorkflowRuntimePromptMixin,
    WorkflowRuntimeReviewMixin,
    WorkflowRuntimePersistenceMixin,
):
    def __init__(
        self,
        workflow_service: WorkflowService,
        chapter_content_service: ChapterContentService,
        context_builder,
        credential_service_factory: Callable[[], CredentialService],
        export_service: ExportService,
        template_renderer: SkillTemplateRenderer,
        tool_provider: ToolProvider,
    ) -> None:
        self.workflow_service = workflow_service
        self.chapter_content_service = chapter_content_service
        self.context_builder = context_builder
        self.credential_service_factory = credential_service_factory
        self.export_service = export_service
        self.template_renderer = template_renderer
        self.tool_provider = tool_provider
        self._credential_service: CredentialService | None = None

    def run(
        self,
        db: Session,
        workflow: WorkflowExecution,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow_config = load_workflow_snapshot(workflow.workflow_snapshot or {})
        while workflow.status == "running":
            node = resolve_node_config(workflow_config, workflow.current_node_id)
            outcome = self._execute_node(db, workflow, workflow_config, node, owner_id=owner_id)
            if self._apply_outcome(workflow, node, outcome):
                break
        return workflow

    def _execute_node(
        self,
        db: Session,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        if node.id == "chapter_split":
            return self._execute_chapter_split(db, workflow, workflow_config, node, owner_id=owner_id)
        if node.id == "chapter_gen":
            return self._execute_chapter_gen(db, workflow, workflow_config, node, owner_id=owner_id)
        if node.node_type == "export":
            return self._execute_export(db, workflow, node)
        raise ConfigurationError(f"Unsupported runtime node: {node.id}")

    def _apply_outcome(
        self,
        workflow: WorkflowExecution,
        node: NodeConfig,
        outcome: NodeOutcome,
    ) -> bool:
        if outcome.pause_reason is not None or outcome.snapshot_extra is not None:
            self.workflow_service.pause(
                workflow,
                reason=outcome.pause_reason,
                current_node_id=node.id,
                resume_from_node=outcome.next_node_id,
            )
            workflow.snapshot = build_runtime_snapshot(workflow, extra=outcome.snapshot_extra)
            return True
        if outcome.next_node_id is None:
            self.workflow_service.complete(workflow, current_node_id=node.id)
            workflow.snapshot = None
            return True
        workflow.current_node_id = outcome.next_node_id
        workflow.snapshot = None
        return False

    def _execute_chapter_split(
        self,
        db: Session,
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
                db,
                workflow,
                workflow_config,
                node,
                chapter_number=None,
            )
            execution.input_data = prompt_bundle["input_data"]
            raw_output = asyncio.run(self._call_llm(db, workflow, prompt_bundle, owner_id=owner_id))
            chapters = self._parse_chapter_split_output(raw_output["content"])
            self._replace_chapter_tasks(db, workflow, chapters)
            self._append_artifact(
                execution,
                "chapter_tasks",
                {"chapters": [item.model_dump() for item in chapters]},
            )
            self._record_prompt_replay(db, execution, prompt_bundle, raw_output)
            self._complete_execution(execution, started_at, {"chapters_count": len(chapters)})
        except Exception as exc:
            self._fail_execution(execution, started_at, exc)
            raise
        return NodeOutcome(
            next_node_id=resolve_next_node_id(workflow.workflow_snapshot or {}, current_node_id=node.id),
            snapshot_extra={"completed_nodes": [self._completed_marker(execution)]},
        )

    def _execute_chapter_gen(
        self,
        db: Session,
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
            prompt_bundle = self._build_prompt_bundle(
                db,
                workflow,
                workflow_config,
                node,
                chapter_number=task.chapter_number,
            )
            prompt_bundle["input_data"]["chapter_task_id"] = str(task.id)
            prompt_bundle["input_data"]["chapter_number"] = task.chapter_number
            execution.input_data = prompt_bundle["input_data"]
            raw_output = asyncio.run(self._call_llm(db, workflow, prompt_bundle, owner_id=owner_id))
            content, version = self.chapter_content_service.save_generated_draft(
                db,
                workflow.project_id,
                task.chapter_number,
                title=task.title,
                content_text=raw_output["content"],
                context_snapshot_hash=prompt_bundle["context_snapshot_hash"],
            )
            task.content_id = content.id
            review_status = self._run_auto_review(
                db,
                workflow,
                workflow_config,
                node,
                execution,
                raw_output["content"],
                owner_id=owner_id,
            )
            self._append_artifact(
                execution,
                "chapter_content",
                {"chapter_number": task.chapter_number, "content_id": str(content.id)},
                content_version_id=version.id,
                word_count=version.word_count,
            )
            self._record_prompt_replay(db, execution, prompt_bundle, raw_output)
            if review_status == "failed":
                task.status = "failed"
                self._fail_execution(execution, started_at, BusinessRuleError("自动审核未通过"))
                return NodeOutcome(
                    next_node_id=node.id,
                    pause_reason="review_failed",
                    snapshot_extra=self._chapter_snapshot(execution, task),
                )
            task.status = WAITING_CONFIRM_TASK_STATUS
            self._complete_execution(
                execution,
                started_at,
                {"chapter_number": task.chapter_number, "content_id": str(content.id)},
            )
        except Exception as exc:
            task.status = "failed"
            self._fail_execution(execution, started_at, exc)
            raise
        return NodeOutcome(next_node_id=node.id, snapshot_extra=self._chapter_snapshot(execution, task))

    def _execute_export(
        self,
        db: Session,
        workflow: WorkflowExecution,
        node: NodeConfig,
    ) -> NodeOutcome:
        execution = self._create_node_execution(db, workflow, node)
        started_at = datetime.now(timezone.utc)
        try:
            exports = self.export_service.export_workflow(
                db,
                workflow,
                formats=list(node.formats),
                config_snapshot=workflow.workflow_snapshot,
            )
            self._append_artifact(
                execution,
                "export",
                {"export_ids": [str(item.id) for item in exports]},
            )
            self._complete_execution(
                execution,
                started_at,
                {"export_ids": [str(item.id) for item in exports]},
            )
        except Exception as exc:
            self._fail_execution(execution, started_at, exc)
            raise
        return NodeOutcome(next_node_id=None)

    async def _call_llm(
        self,
        db: Session,
        workflow: WorkflowExecution,
        prompt_bundle: dict[str, Any],
        *,
        owner_id: uuid.UUID,
    ) -> dict[str, Any]:
        model = prompt_bundle["model"]
        credential_service = self._resolve_credential_service()
        credential = credential_service.resolve_active_credential(
            db,
            provider=model.provider or "",
            user_id=owner_id,
            project_id=workflow.project_id,
        )
        return await self.tool_provider.execute(
            LLM_GENERATE_TOOL,
            {
                "prompt": prompt_bundle["prompt"],
                "system_prompt": prompt_bundle["system_prompt"],
                "model": model.model_dump(mode="json", exclude_none=True),
                "credential": {
                    "api_key": credential_service.crypto.decrypt(credential.encrypted_key),
                    "base_url": credential.base_url,
                },
                "response_format": prompt_bundle["response_format"],
            },
        )

    def _resolve_credential_service(self) -> CredentialService:
        if self._credential_service is None:
            self._credential_service = self.credential_service_factory()
        return self._credential_service
