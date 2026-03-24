from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.service import BillingService
from app.modules.config_registry.schemas.config_schemas import NodeConfig, WorkflowConfig
from app.modules.content.service import ChapterContentService
from app.modules.context.engine import ContextBuilder
from app.modules.credential.models import ModelCredential
from app.modules.credential.service import CredentialService
from app.modules.export.service import ExportService
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime import SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import BudgetExceededError, ConfigurationError
from app.shared.runtime.llm_tool_provider import LLM_GENERATE_TOOL

from .snapshot_support import build_runtime_snapshot, load_workflow_snapshot, resolve_node_config
from .workflow_runtime_chapter_candidate_mixin import WorkflowRuntimeChapterCandidateMixin
from .workflow_runtime_execute_mixin import WorkflowRuntimeExecuteMixin
from .workflow_runtime_export_mixin import WorkflowRuntimeExportMixin
from .workflow_runtime_fix_mixin import WorkflowRuntimeFixMixin
from .workflow_runtime_persistence_mixin import WorkflowRuntimePersistenceMixin
from .workflow_runtime_prompt_mixin import WorkflowRuntimePromptMixin
from .workflow_runtime_review_mixin import WorkflowRuntimeReviewMixin
from .workflow_runtime_shared import NodeOutcome
from .workflow_runtime_task_mixin import WorkflowRuntimeTaskMixin
from .workflow_service import WorkflowService


class WorkflowRuntimeService(
    WorkflowRuntimeExecuteMixin,
    WorkflowRuntimeChapterCandidateMixin,
    WorkflowRuntimeTaskMixin,
    WorkflowRuntimePromptMixin,
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
    ) -> None:
        self.workflow_service = workflow_service
        self.billing_service = billing_service
        self.chapter_content_service = chapter_content_service
        self.context_builder = context_builder
        self.credential_service_factory = credential_service_factory
        self.export_service = export_service
        self.template_renderer = template_renderer
        self.tool_provider = tool_provider
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

    async def _call_llm(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        prompt_bundle: dict[str, Any],
        *,
        owner_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        usage_type: str,
        credential: ModelCredential | None = None,
    ) -> dict[str, Any]:
        model = prompt_bundle["model"]
        credential_service = self._resolve_credential_service()
        resolved_credential = credential
        if resolved_credential is None:
            resolved_credential = await credential_service.resolve_active_credential(
                db,
                provider=model.provider or "",
                user_id=owner_id,
                project_id=workflow.project_id,
            )
        raw_output = await self.tool_provider.execute(
            LLM_GENERATE_TOOL,
            {
                "prompt": prompt_bundle["prompt"],
                "system_prompt": prompt_bundle["system_prompt"],
                "model": model.model_dump(mode="json", exclude_none=True),
                "credential": {
                    "api_key": credential_service.crypto.decrypt(resolved_credential.encrypted_key),
                    "api_dialect": resolved_credential.api_dialect,
                    "base_url": resolved_credential.base_url,
                    "default_model": resolved_credential.default_model,
                },
                "response_format": prompt_bundle["response_format"],
            },
        )
        budget_result = await self.billing_service.record_usage_and_check_budget(
            db,
            workflow_execution_id=workflow.id,
            project_id=workflow.project_id,
            user_id=owner_id,
            node_execution_id=node_execution_id,
            credential_id=resolved_credential.id,
            usage_type=usage_type,
            model_name=raw_output.get("model_name") or "",
            input_tokens=raw_output.get("input_tokens"),
            output_tokens=raw_output.get("output_tokens"),
            budget_config=workflow_config.budget,
        )
        self._record_budget_warnings(
            db,
            workflow_execution_id=workflow.id,
            node_execution_id=node_execution_id,
            budget_result=budget_result,
        )
        exceeded = budget_result.exceeded_status
        if exceeded is not None:
            raise BudgetExceededError(
                self._budget_exceeded_message(exceeded.scope, exceeded.used_tokens, exceeded.limit_tokens),
                action=workflow_config.budget.on_exceed,
                scope=exceeded.scope,
                used_tokens=exceeded.used_tokens,
                limit_tokens=exceeded.limit_tokens,
                usage_type=usage_type,
                raw_output=raw_output,
            )
        return raw_output

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
