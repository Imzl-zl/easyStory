from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.modules.observability.models import PromptReplay
from app.modules.workflow.models import Artifact, ChapterTask, NodeExecution

from .snapshot_support import resolve_node_order


class WorkflowRuntimePersistenceMixin:
    def _create_node_execution(self, db: Session, workflow, node) -> NodeExecution:
        execution = NodeExecution(
            workflow_execution_id=workflow.id,
            node_id=node.id,
            sequence=self._next_sequence(db, workflow.id, node.id),
            node_order=resolve_node_order(workflow.workflow_snapshot or {}, node.id),
            node_type=node.node_type,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(execution)
        db.flush()
        return execution

    def _next_sequence(self, db: Session, workflow_execution_id: uuid.UUID, node_id: str) -> int:
        existing = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.workflow_execution_id == workflow_execution_id,
                NodeExecution.node_id == node_id,
            )
            .order_by(NodeExecution.sequence.desc())
            .first()
        )
        return 0 if existing is None else existing.sequence + 1

    def _complete_execution(self, execution: NodeExecution, started_at: datetime, output_data: dict[str, Any]) -> None:
        finished_at = datetime.now(timezone.utc)
        execution.status = "completed"
        execution.output_data = output_data
        execution.completed_at = finished_at
        execution.execution_time_ms = int((finished_at - started_at).total_seconds() * 1000)

    def _fail_execution(self, execution: NodeExecution, started_at: datetime, exc: Exception) -> None:
        finished_at = datetime.now(timezone.utc)
        execution.status = "failed"
        execution.error_message = str(exc)
        execution.completed_at = finished_at
        execution.execution_time_ms = int((finished_at - started_at).total_seconds() * 1000)

    def _append_artifact(
        self,
        execution: NodeExecution,
        artifact_type: str,
        payload: dict[str, Any],
        *,
        content_version_id: uuid.UUID | None = None,
        word_count: int | None = None,
    ) -> None:
        execution.artifacts.append(
            Artifact(
                artifact_type=artifact_type,
                content_version_id=content_version_id,
                payload=payload,
                word_count=word_count,
            )
        )

    def _record_prompt_replay(
        self,
        db: Session,
        execution: NodeExecution,
        prompt_bundle: dict[str, Any],
        raw_output: dict[str, Any],
    ) -> None:
        db.add(
            PromptReplay(
                node_execution_id=execution.id,
                replay_type="generate",
                model_name=prompt_bundle["model"].name or "",
                prompt_text=prompt_bundle["prompt"],
                response_text=self._serialize_replay_text(raw_output.get("content")),
                input_tokens=raw_output.get("input_tokens"),
                output_tokens=raw_output.get("output_tokens"),
            )
        )

    def _chapter_snapshot(self, execution: NodeExecution, task: ChapterTask) -> dict[str, Any]:
        return {
            "current_node_execution_id": str(execution.id),
            "current_chapter_number": task.chapter_number,
            "pending_actions": [
                {
                    "type": "chapter_confirmation",
                    "chapter_number": task.chapter_number,
                    "content_id": str(task.content_id) if task.content_id is not None else None,
                }
            ],
        }

    def _completed_marker(self, execution: NodeExecution) -> dict[str, Any]:
        return {"node_id": execution.node_id, "sequence": execution.sequence, "status": execution.status}
