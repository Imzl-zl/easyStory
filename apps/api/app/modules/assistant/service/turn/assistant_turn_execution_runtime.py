from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse


class AssistantTurnExecutionRuntime:
    def __init__(
        self,
        *,
        run_before_hooks: Callable[[], Awaitable[list[Any]]],
        call_turn_llm: Callable[[], Awaitable[LLMGenerateToolResponse]],
        finalize_response: Callable[[list[Any], LLMGenerateToolResponse], Awaitable[Any]],
        run_prepared_on_error_hooks: Callable[[Exception], Awaitable[Exception | None]],
        store_terminal_turn: Callable[..., Awaitable[None]],
    ) -> None:
        self.run_before_hooks = run_before_hooks
        self.call_turn_llm = call_turn_llm
        self.finalize_response = finalize_response
        self.run_prepared_on_error_hooks = run_prepared_on_error_hooks
        self.store_terminal_turn = store_terminal_turn

    async def run(self) -> Any:
        try:
            before_results = await self.run_before_hooks()
            raw_output = await self.call_turn_llm()
            response = await self.finalize_response(before_results, raw_output)
        except Exception as exc:
            hook_error = await self.run_prepared_on_error_hooks(exc)
            await self.store_terminal_turn(error=hook_error or exc)
            if hook_error is not None:
                raise hook_error
            raise
        if response is None:
            raise ConfigurationError("Assistant turn execution completed without response")
        await self.store_terminal_turn(response=response)
        return response
