from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError


class AssistantTurnRecoveryRuntime:
    def __init__(
        self,
        *,
        resolve_existing_run: Callable[[], Awaitable[Any | None]],
        recover_existing_running_turn: Callable[[Any], Awaitable[None]],
        recover_existing_turn: Callable[[Any], Any | None],
        build_running_turn_record: Callable[[], Any],
        create_run: Callable[[Any], Awaitable[bool]],
        reload_existing_run_after_conflict: Callable[[], Awaitable[Any | None]],
    ) -> None:
        self.resolve_existing_run = resolve_existing_run
        self.recover_existing_running_turn = recover_existing_running_turn
        self.recover_existing_turn = recover_existing_turn
        self.build_running_turn_record = build_running_turn_record
        self.create_run = create_run
        self.reload_existing_run_after_conflict = reload_existing_run_after_conflict

    async def run(self) -> Any | None:
        existing_run = await self.resolve_existing_run()
        if existing_run is not None:
            await self.recover_existing_running_turn(existing_run)
            return self.recover_existing_turn(existing_run)
        running_record = self.build_running_turn_record()
        if await self.create_run(running_record):
            return None
        conflict_run = await self.reload_existing_run_after_conflict()
        if conflict_run is None:
            raise ConfigurationError(
                "Assistant turn run snapshot disappeared after create_run conflict"
            )
        await self.recover_existing_running_turn(conflict_run)
        return self.recover_existing_turn(conflict_run)
