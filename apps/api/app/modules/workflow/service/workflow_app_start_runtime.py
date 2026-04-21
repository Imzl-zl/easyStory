from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError

class WorkflowAppStartRuntime:
    def __init__(
        self,
        *,
        resolve_workflow_config: Callable[[], Any],
        ensure_preconditions: Callable[[], Awaitable[None]],
        build_execution: Callable[[Any], Any],
        persist_started_workflow: Callable[[Any, Any], Awaitable[None]],
        dispatch_runtime: Callable[[Any], Awaitable[None]],
    ) -> None:
        self.resolve_workflow_config = resolve_workflow_config
        self.ensure_preconditions = ensure_preconditions
        self.build_execution = build_execution
        self.persist_started_workflow = persist_started_workflow
        self.dispatch_runtime = dispatch_runtime

    async def run(self):
        workflow_config = self.resolve_workflow_config()
        await self.ensure_preconditions()
        workflow = self.build_execution(workflow_config)
        await self.persist_started_workflow(workflow, workflow_config)
        execution_id = getattr(workflow, "id", None)
        if execution_id is None:
            raise ConfigurationError("Workflow app start runtime missing workflow id after persist")
        await self.dispatch_runtime(execution_id)
        return execution_id
