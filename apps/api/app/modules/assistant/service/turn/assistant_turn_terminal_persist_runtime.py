from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError


class LangGraphAssistantTurnTerminalPersistRuntime:
    def __init__(
        self,
        *,
        resolve_existing_run: Callable[[], Awaitable[Any | None]],
        build_terminal_record: Callable[[Any | None], Any],
        save_run: Callable[[Any], Awaitable[None]],
    ) -> None:
        self.resolve_existing_run = resolve_existing_run
        self.build_terminal_record = build_terminal_record
        self.save_run = save_run

    async def run(self) -> None:
        existing_run = await self.resolve_existing_run()
        record = self.build_terminal_record(existing_run)
        if record is None:
            raise ConfigurationError("Assistant terminal persist runtime missing terminal record")
        await self.save_run(record)
