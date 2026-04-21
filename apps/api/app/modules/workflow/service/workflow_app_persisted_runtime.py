from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import BusinessRuleError

class WorkflowAppPersistedRuntime:
    def __init__(
        self,
        *,
        load_workflow: Callable[[], Awaitable[Any]],
        run_runtime: Callable[[Any], Awaitable[None]],
        commit: Callable[[], Awaitable[None]],
        recover_runtime_failure: Callable[[str | None, str, str | None], Awaitable[None]],
    ) -> None:
        self.load_workflow = load_workflow
        self.run_runtime = run_runtime
        self.commit = commit
        self.recover_runtime_failure = recover_runtime_failure
        self.current_node_id: str | None = None

    async def run(self) -> None:
        try:
            workflow = await self.load_workflow()
            self.current_node_id = getattr(workflow, "current_node_id", None)
            await self.run_runtime(workflow)
            await self.commit()
        except Exception as exc:
            reason = None if isinstance(exc, BusinessRuleError) else "error"
            await self.recover_runtime_failure(
                self.current_node_id,
                str(exc),
                reason,
            )
            raise


LangGraphWorkflowAppPersistedRuntime = WorkflowAppPersistedRuntime
