from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError


class AssistantTurnFinalizeRuntime:
    def __init__(
        self,
        *,
        resolve_content: Callable[[], str],
        build_after_payload: Callable[[str], dict[str, Any]],
        run_after_hooks: Callable[[dict[str, Any]], Awaitable[list[Any]]],
        build_response: Callable[[str, list[Any]], Any],
    ) -> None:
        self.resolve_content = resolve_content
        self.build_after_payload = build_after_payload
        self.run_after_hooks = run_after_hooks
        self.build_response = build_response

    async def run(self) -> Any:
        content = self.resolve_content()
        after_payload = self.build_after_payload(content)
        after_results = await self.run_after_hooks(after_payload)
        response = self.build_response(content, after_results)
        if response is None:
            raise ConfigurationError("Assistant turn finalize runtime completed without response")
        return response


LangGraphAssistantTurnFinalizeRuntime = AssistantTurnFinalizeRuntime
