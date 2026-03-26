from __future__ import annotations

import asyncio
from typing import Any, Protocol

from .errors import ConfigurationError


class PluginProvider(Protocol):
    async def execute(self, *, config: dict[str, Any], context: Any) -> Any: ...


class PluginRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, PluginProvider] = {}

    def register(self, name: str, provider: PluginProvider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> PluginProvider:
        if name not in self._providers:
            raise KeyError(f"Plugin provider not found: {name}")
        return self._providers[name]

    async def execute(
        self,
        plugin_type: str,
        *,
        config: dict[str, Any],
        context: Any,
        timeout_seconds: int | None = None,
    ) -> Any:
        provider = self.get(plugin_type)
        if timeout_seconds is None:
            return await provider.execute(config=config, context=context)
        if timeout_seconds <= 0:
            raise ConfigurationError("Plugin timeout_seconds must be > 0")
        return await asyncio.wait_for(
            provider.execute(config=config, context=context),
            timeout=timeout_seconds,
        )
