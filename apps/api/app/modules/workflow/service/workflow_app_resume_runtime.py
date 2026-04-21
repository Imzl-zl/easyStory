from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError

class WorkflowAppResumeRuntime:
    def __init__(
        self,
        *,
        ensure_resume_allowed: Callable[[], Awaitable[None]],
        resume_workflow: Callable[[], Awaitable[Any]],
        dispatch_runtime: Callable[[Any], Awaitable[None]],
    ) -> None:
        self.ensure_resume_allowed = ensure_resume_allowed
        self.resume_workflow = resume_workflow
        self.dispatch_runtime = dispatch_runtime

    async def run(self):
        await self.ensure_resume_allowed()
        workflow = await self.resume_workflow()
        execution_id = getattr(workflow, "id", None)
        if execution_id is None:
            raise ConfigurationError("Workflow app resume runtime missing workflow id")
        await self.dispatch_runtime(execution_id)
        return execution_id


LangGraphWorkflowAppResumeRuntime = WorkflowAppResumeRuntime
