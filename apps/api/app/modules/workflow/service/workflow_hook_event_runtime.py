from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class WorkflowHookEventRuntime:
    def __init__(
        self,
        *,
        resolve_hooks: Callable[[], list[Any]],
        matches_condition: Callable[[Any], bool],
        record_skip: Callable[[Any], None],
        execute_hook: Callable[[Any], Awaitable[Any]],
        record_success: Callable[[Any, Any], None],
    ) -> None:
        self.resolve_hooks = resolve_hooks
        self.matches_condition = matches_condition
        self.record_skip = record_skip
        self.execute_hook = execute_hook
        self.record_success = record_success

    async def run(self) -> list[Any]:
        hooks = self.resolve_hooks()
        results: list[Any] = []
        for hook in hooks:
            if not self.matches_condition(hook):
                self.record_skip(hook)
                continue
            result = await self.execute_hook(hook)
            self.record_success(hook, result)
            results.append(result)
        return results
