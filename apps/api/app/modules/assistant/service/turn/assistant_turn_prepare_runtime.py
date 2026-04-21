from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.modules.config_registry.schemas import HookConfig
from app.shared.runtime.errors import ConfigurationError

from ..dto import AssistantTurnResponseDTO
from .assistant_turn_runtime_support import PreparedAssistantTurn


@dataclass(frozen=True)
class AssistantTurnPrepareRuntimeResult:
    resolved_hooks: list[HookConfig]
    prepared: PreparedAssistantTurn
    replayed_response: AssistantTurnResponseDTO | None


class AssistantTurnPrepareRuntime:
    def __init__(
        self,
        *,
        resolve_hooks: Callable[[], list[HookConfig]],
        prepare_turn: Callable[[list[HookConfig]], Awaitable[PreparedAssistantTurn]],
        run_prepare_on_error_hooks: Callable[[list[HookConfig], Exception], Awaitable[Exception | None]],
        recover_or_start_turn: Callable[[PreparedAssistantTurn], Awaitable[AssistantTurnResponseDTO | None]],
    ) -> None:
        self.resolve_hooks = resolve_hooks
        self.prepare_turn = prepare_turn
        self.run_prepare_on_error_hooks = run_prepare_on_error_hooks
        self.recover_or_start_turn = recover_or_start_turn

    async def run(self) -> AssistantTurnPrepareRuntimeResult:
        resolved_hooks: list[HookConfig] = []
        try:
            resolved_hooks = self.resolve_hooks()
            prepared = await self.prepare_turn(resolved_hooks)
        except Exception as exc:
            hook_error = await self.run_prepare_on_error_hooks(list(resolved_hooks), exc)
            if hook_error is not None:
                raise hook_error
            raise
        if prepared is None:
            raise ConfigurationError("Assistant turn prepare runtime completed without prepared turn")
        replayed_response = await self.recover_or_start_turn(prepared)
        return AssistantTurnPrepareRuntimeResult(
            resolved_hooks=list(resolved_hooks),
            prepared=prepared,
            replayed_response=replayed_response,
        )


LangGraphAssistantTurnPrepareRuntime = AssistantTurnPrepareRuntime
