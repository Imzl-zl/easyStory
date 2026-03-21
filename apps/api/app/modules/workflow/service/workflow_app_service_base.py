from __future__ import annotations

from app.modules.config_registry.schemas.config_schemas import WorkflowConfig
from app.modules.observability.models import ExecutionLog
from app.modules.project.models import Project
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .snapshot_support import dump_config, freeze_agents, freeze_skills, freeze_workflow

PREPARATION_ASSET_LABELS = {
    "outline": "大纲",
    "opening_plan": "开篇设计",
}


class WorkflowAppServiceBase:
    def __init__(
        self,
        *,
        workflow_service,
        project_service,
        config_loader,
        runtime_service,
    ) -> None:
        self.workflow_service = workflow_service
        self.project_service = project_service
        self.config_loader = config_loader
        self.runtime_service = runtime_service

    def _resolve_workflow_config(
        self,
        project: Project,
        requested_workflow_id: str | None,
    ) -> WorkflowConfig:
        workflow_id = requested_workflow_id or _extract_template_workflow_id(project)
        if workflow_id is None:
            raise BusinessRuleError("项目未绑定默认工作流，请显式指定 workflow_id")
        return self.config_loader.load_workflow(workflow_id)

    def _build_execution(
        self,
        project: Project,
        workflow_config: WorkflowConfig,
    ) -> WorkflowExecution:
        agents = freeze_agents(self.config_loader, workflow_config)
        return WorkflowExecution(
            project_id=project.id,
            template_id=project.template_id,
            status="created",
            workflow_snapshot=freeze_workflow(
                self.config_loader,
                workflow_config,
            ),
            skills_snapshot=freeze_skills(
                self.config_loader,
                workflow_config,
                agents,
            ),
            agents_snapshot={agent.id: dump_config(agent) for agent in agents},
        )

    def _record_workflow_log(
        self,
        db,
        workflow: WorkflowExecution,
        *,
        level: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        db.add(
            ExecutionLog(
                workflow_execution_id=workflow.id,
                node_execution_id=None,
                level=level,
                message=message,
                details=details,
            )
        )


def _extract_template_workflow_id(project: Project) -> str | None:
    template = project.template
    if template is None or template.config is None:
        return None
    workflow_id = template.config.get("workflow_id")
    if workflow_id is None:
        return None
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ConfigurationError("Template.config.workflow_id must be a non-empty string")
    return workflow_id
