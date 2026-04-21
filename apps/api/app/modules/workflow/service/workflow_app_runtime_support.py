from __future__ import annotations

from collections.abc import Callable
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .workflow_app_persisted_runtime import WorkflowAppPersistedRuntime
from .snapshot_support import build_runtime_snapshot

RuntimeDispatchFn = Callable[[uuid.UUID, uuid.UUID], None]


class WorkflowAppRuntimeSupportMixin:
    async def _dispatch_runtime(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        runtime_dispatcher: RuntimeDispatchFn | None,
    ) -> None:
        if runtime_dispatcher is not None:
            runtime_dispatcher(workflow_id, owner_id)
            return
        await self.run_workflow_runtime(db, workflow_id, owner_id=owner_id)

    async def run_workflow_runtime(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        runtime = WorkflowAppPersistedRuntime(
            load_workflow=lambda: self._require_workflow_for_update(
                db,
                workflow_id,
                owner_id=owner_id,
            ),
            run_runtime=lambda workflow: self.runtime_service.run(
                db,
                workflow,
                owner_id=owner_id,
            ),
            commit=db.commit,
            recover_runtime_failure=lambda current_node_id, detail, reason: self._recover_runtime_failure(
                db,
                workflow_id=workflow_id,
                owner_id=owner_id,
                current_node_id=current_node_id,
                detail=detail,
                reason=reason,
            ),
        )
        await runtime.run()

    async def _run_persisted_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        await self.run_workflow_runtime(db, workflow_id, owner_id=owner_id)

    async def _recover_runtime_failure(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        current_node_id: str | None,
        detail: str,
        reason: str | None,
    ) -> None:
        await db.rollback()
        workflow = await self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        self.workflow_service.pause(
            workflow,
            reason=reason,
            current_node_id=current_node_id,
            resume_from_node=current_node_id,
        )
        workflow.snapshot = build_runtime_snapshot(
            workflow,
            extra={"pending_actions": [{"type": "runtime_error", "detail": detail}]},
        )
        self._record_workflow_log(
            db,
            workflow,
            level="ERROR",
            message="Workflow paused after runtime error",
            details={"detail": detail, "reason": reason},
        )
        await db.commit()
