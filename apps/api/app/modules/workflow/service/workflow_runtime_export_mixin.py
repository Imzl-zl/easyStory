from __future__ import annotations

from datetime import datetime, timezone

from app.modules.config_registry.schemas.config_schemas import NodeConfig
from app.modules.workflow.models import WorkflowExecution

from .workflow_runtime_shared import NodeOutcome


class WorkflowRuntimeExportMixin:
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
                db,
                workflow,
                formats=list(node.formats),
                config_snapshot=workflow.workflow_snapshot,
            )
            export_ids = [str(item.id) for item in exports]
            self._append_artifact(execution, "export", {"export_ids": export_ids})
            self._complete_execution(db, execution, started_at, {"export_ids": export_ids})
        except Exception as exc:
            self._fail_execution(db, execution, started_at, exc)
            raise
        return NodeOutcome(next_node_id=None)
