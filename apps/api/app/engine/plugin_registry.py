from typing import Any


class PluginRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}

    def register(self, name: str, provider: Any) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> Any:
        if name not in self._providers:
            raise KeyError(f"Plugin provider not found: {name}")
        return self._providers[name]
