from __future__ import annotations

from collections.abc import Awaitable, Callable

from .workflow_runtime_shared import NodeOutcome

class WorkflowNodeExecutionRuntime:
    def __init__(
        self,
        *,
        run_before_hook: Callable[[], Awaitable[object]],
        run_before_on_error: Callable[[Exception], Awaitable[None]],
        dispatch_node: Callable[[], Awaitable[NodeOutcome]],
        run_dispatch_on_error: Callable[[Exception], Awaitable[None]],
        run_after_hook: Callable[[NodeOutcome], Awaitable[object]],
        run_after_on_error: Callable[[NodeOutcome, Exception], Awaitable[None]],
    ) -> None:
        self.run_before_hook = run_before_hook
        self.run_before_on_error = run_before_on_error
        self.dispatch_node = dispatch_node
        self.run_dispatch_on_error = run_dispatch_on_error
        self.run_after_hook = run_after_hook
        self.run_after_on_error = run_after_on_error

    async def run(self) -> NodeOutcome:
        try:
            await self.run_before_hook()
        except Exception as exc:
            await self.run_before_on_error(exc)
            raise
        try:
            outcome = await self.dispatch_node()
        except Exception as exc:
            await self.run_dispatch_on_error(exc)
            raise
        try:
            await self.run_after_hook(outcome)
        except Exception as exc:
            await self.run_after_on_error(outcome, exc)
            raise
        return outcome
