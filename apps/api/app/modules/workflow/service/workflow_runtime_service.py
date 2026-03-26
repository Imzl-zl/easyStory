from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.service import BillingService
from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.content.service import ChapterContentService
from app.modules.context.engine import ContextBuilder
from app.modules.credential.service import CredentialService
from app.modules.export.service import ExportService
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime import PluginRegistry, SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import ConfigurationError

from .workflow_hook_providers import build_workflow_plugin_registry
from .snapshot_support import build_runtime_snapshot, load_workflow_snapshot, resolve_node_config
from .workflow_runtime_chapter_candidate_mixin import WorkflowRuntimeChapterCandidateMixin
from .workflow_runtime_execute_mixin import WorkflowRuntimeExecuteMixin
from .workflow_runtime_export_mixin import WorkflowRuntimeExportMixin
from .workflow_runtime_fix_mixin import WorkflowRuntimeFixMixin
from .workflow_runtime_hook_mixin import WorkflowRuntimeHookMixin
from .workflow_runtime_llm_mixin import WorkflowRuntimeLlmMixin
from .workflow_runtime_persistence_mixin import WorkflowRuntimePersistenceMixin
from .workflow_runtime_prompt_mixin import WorkflowRuntimePromptMixin
from .workflow_runtime_review_mixin import WorkflowRuntimeReviewMixin
from .workflow_runtime_shared import NodeOutcome
from .workflow_runtime_task_mixin import WorkflowRuntimeTaskMixin
from .workflow_service import WorkflowService


class WorkflowRuntimeService(
    WorkflowRuntimeHookMixin,
    WorkflowRuntimeExecuteMixin,
    WorkflowRuntimeChapterCandidateMixin,
    WorkflowRuntimeTaskMixin,
    WorkflowRuntimePromptMixin,
    WorkflowRuntimeLlmMixin,
    WorkflowRuntimeReviewMixin,
    WorkflowRuntimeFixMixin,
    WorkflowRuntimeExportMixin,
    WorkflowRuntimePersistenceMixin,
):
    def __init__(
        self,
        workflow_service: WorkflowService,
        billing_service: BillingService,
        chapter_content_service: ChapterContentService,
        context_builder: ContextBuilder,
        credential_service_factory: Callable[[], CredentialService],
        export_service: ExportService,
        template_renderer: SkillTemplateRenderer,
        tool_provider: ToolProvider,
        plugin_registry: PluginRegistry | None = None,
    ) -> None:
        self.workflow_service = workflow_service
        self.billing_service = billing_service
        self.chapter_content_service = chapter_content_service
        self.context_builder = context_builder
        self.credential_service_factory = credential_service_factory
        self.export_service = export_service
        self.template_renderer = template_renderer
        self.tool_provider = tool_provider
        self.plugin_registry = plugin_registry or build_workflow_plugin_registry(self)
        self._credential_service: CredentialService | None = None

    async def run(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow_config = load_workflow_snapshot(workflow.workflow_snapshot or {})
        while workflow.status == "running":
            node = resolve_node_config(workflow_config, workflow.current_node_id)
            outcome = await self._execute_node(db, workflow, workflow_config, node, owner_id=owner_id)
            if self._apply_outcome(db, workflow, node, outcome):
                break
        return workflow

    async def _execute_node(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        before_context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "before_node_start",
            owner_id=owner_id,
            payload=self._base_hook_payload(workflow, workflow_config, node, "before_node_start"),
        )
        try:
            await self._run_hook_event(before_context)
        except Exception as exc:
            await self._run_on_error_hooks(
                self._build_hook_context(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    "on_error",
                    owner_id=owner_id,
                    payload=self._base_hook_payload(workflow, workflow_config, node, "on_error"),
                ),
                exc,
            )
            raise
        return await self._execute_node_body(db, workflow, workflow_config, node, owner_id=owner_id)

    async def _execute_node_body(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        try:
            outcome = await self._dispatch_node(db, workflow, workflow_config, node, owner_id=owner_id)
        except Exception as exc:
            await self._run_on_error_hooks(
                self._build_hook_context(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    "on_error",
                    owner_id=owner_id,
                    payload=self._base_hook_payload(workflow, workflow_config, node, "on_error"),
                ),
                exc,
            )
            raise
        after_payload = self._after_node_payload(outcome)
        after_context = self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            "after_node_end",
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                "after_node_end",
                node_execution_id=outcome.node_execution_id,
                extra=after_payload,
            ),
            node_execution_id=outcome.node_execution_id,
        )
        try:
            await self._run_hook_event(after_context)
        except Exception as exc:
            await self._run_on_error_hooks(after_context, exc)
            raise
        return outcome

    async def _dispatch_node(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        if node.id == "chapter_split":
            return await self._execute_chapter_split(
                db,
                workflow,
                workflow_config,
                node,
                owner_id=owner_id,
            )
        if node.id == "chapter_gen":
            return await self._execute_chapter_gen(
                db,
                workflow,
                workflow_config,
                node,
                owner_id=owner_id,
            )
        if node.node_type == "export":
            return await self._execute_export(db, workflow, node)
        raise ConfigurationError(f"Unsupported runtime node: {node.id}")

    def _after_node_payload(self, outcome: NodeOutcome) -> dict[str, object]:
        payload: dict[str, object] = {
            "next_node_id": outcome.next_node_id,
            "pause_reason": outcome.pause_reason,
            "workflow_status": outcome.workflow_status,
        }
        if outcome.hook_payload:
            payload.update(outcome.hook_payload)
        return payload

    def _apply_outcome(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        node: NodeConfig,
        outcome: NodeOutcome,
    ) -> bool:
        if outcome.workflow_status == "failed":
            self.workflow_service.fail(
                workflow,
                current_node_id=outcome.next_node_id or node.id,
            )
            workflow.snapshot = build_runtime_snapshot(workflow, extra=outcome.snapshot_extra)
            self._record_execution_log(
                db,
                workflow_execution_id=workflow.id,
                node_execution_id=None,
                level="ERROR",
                message="Workflow failed",
                details={"node_id": node.id},
            )
            return True
        if outcome.pause_reason is not None or outcome.snapshot_extra is not None:
            self.workflow_service.pause(
                workflow,
                reason=outcome.pause_reason,
                current_node_id=node.id,
                resume_from_node=outcome.next_node_id,
            )
            workflow.snapshot = build_runtime_snapshot(workflow, extra=outcome.snapshot_extra)
            self._record_execution_log(
                db,
                workflow_execution_id=workflow.id,
                node_execution_id=None,
                level="WARNING" if outcome.pause_reason else "INFO",
                message="Workflow paused",
                details={"node_id": node.id, "reason": outcome.pause_reason},
            )
            return True
        if outcome.next_node_id is None:
            self.workflow_service.complete(workflow, current_node_id=node.id)
            workflow.snapshot = None
            self._record_execution_log(
                db,
                workflow_execution_id=workflow.id,
                node_execution_id=None,
                level="INFO",
                message="Workflow completed",
                details={"node_id": node.id},
            )
            return True
        workflow.current_node_id = outcome.next_node_id
        workflow.snapshot = None
        return False

    def _resolve_credential_service(self) -> CredentialService:
        if self._credential_service is None:
            self._credential_service = self.credential_service_factory()
        return self._credential_service

    def _record_budget_warnings(
        self,
        db: AsyncSession,
        *,
        workflow_execution_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        budget_result,
    ) -> None:
        warning_scopes = [
            status.scope
            for status in budget_result.statuses
            if status.warning_reached and not status.exceeded
        ]
        if not warning_scopes:
            return
        self._record_execution_log(
            db,
            workflow_execution_id=workflow_execution_id,
            node_execution_id=node_execution_id,
            level="WARNING",
            message="Budget warning threshold reached",
            details={"scopes": warning_scopes},
        )

    def _budget_exceeded_message(
        self,
        scope: str,
        used_tokens: int,
        limit_tokens: int,
    ) -> str:
        return f"预算超限({scope}): used_tokens={used_tokens}, limit_tokens={limit_tokens}"
