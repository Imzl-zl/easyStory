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
from app.shared.runtime.plugins.plugin_registry import PluginRegistry
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.tool_provider import ToolProvider
from app.shared.runtime.errors import ConfigurationError

from .workflow_hook_providers import build_workflow_plugin_registry
from .workflow_hook_agent_runtime import LangGraphWorkflowHookAgentRuntime
from .workflow_node_execution_runtime import LangGraphWorkflowNodeExecutionRuntime
from .workflow_outcome_runtime import LangGraphWorkflowOutcomeRuntime
from .snapshot_support import load_workflow_snapshot
from .workflow_graph_runtime import WorkflowGraphRuntime
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
        self.workflow_hook_agent_runtime = LangGraphWorkflowHookAgentRuntime(
            template_renderer=self.template_renderer,
            llm_caller=self._call_llm,
            parse_json=self._parse_json,
        )
        self._credential_service: CredentialService | None = None

    async def run(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow_config = load_workflow_snapshot(workflow.workflow_snapshot or {})
        graph_runtime = WorkflowGraphRuntime(
            self,
            db=db,
            workflow=workflow,
            workflow_config=workflow_config,
            owner_id=owner_id,
        )
        return await graph_runtime.run()

    async def _execute_node(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        owner_id: uuid.UUID,
    ) -> NodeOutcome:
        runtime = LangGraphWorkflowNodeExecutionRuntime(
            run_before_hook=lambda: self._run_hook_event(
                self._build_node_event_context(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    "before_node_start",
                    owner_id=owner_id,
                )
            ),
            run_before_on_error=lambda error: self._run_on_error_hooks(
                self._build_node_event_context(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    "on_error",
                    owner_id=owner_id,
                ),
                error,
            ),
            dispatch_node=lambda: self._dispatch_node(
                db,
                workflow,
                workflow_config,
                node,
                owner_id=owner_id,
            ),
            run_dispatch_on_error=lambda error: self._run_on_error_hooks(
                self._build_node_event_context(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    "on_error",
                    owner_id=owner_id,
                ),
                error,
            ),
            run_after_hook=lambda outcome: self._run_hook_event(
                self._build_node_event_context(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    "after_node_end",
                    owner_id=owner_id,
                    node_execution_id=outcome.node_execution_id,
                    extra=self._after_node_payload(outcome),
                )
            ),
            run_after_on_error=lambda outcome, error: self._run_on_error_hooks(
                self._build_node_event_context(
                    db,
                    workflow,
                    workflow_config,
                    node,
                    "after_node_end",
                    owner_id=owner_id,
                    node_execution_id=outcome.node_execution_id,
                    extra=self._after_node_payload(outcome),
                ),
                error,
            ),
        )
        return await runtime.run()

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

    def _build_node_event_context(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        event: str,
        *,
        owner_id: uuid.UUID,
        node_execution_id: uuid.UUID | None = None,
        extra: dict[str, object] | None = None,
    ):
        return self._build_hook_context(
            db,
            workflow,
            workflow_config,
            node,
            event,
            owner_id=owner_id,
            payload=self._base_hook_payload(
                workflow,
                workflow_config,
                node,
                event,
                node_execution_id=node_execution_id,
                extra=extra,
            ),
            node_execution_id=node_execution_id,
        )

    def _apply_outcome(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        node: NodeConfig,
        outcome: NodeOutcome,
    ) -> bool:
        runtime = LangGraphWorkflowOutcomeRuntime(
            workflow_service=self.workflow_service,
            record_execution_log=self._record_execution_log,
            db=db,
            workflow=workflow,
            node=node,
            outcome=outcome,
        )
        return runtime.run()

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
