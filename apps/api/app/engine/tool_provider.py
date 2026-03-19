from abc import ABC, abstractmethod
from typing import Any


class ToolProvider(ABC):
    @abstractmethod
    async def execute(self, tool_name: str, params: dict[str, Any]) -> Any:
        raise NotImplementedError

    @abstractmethod
    def list_tools(self) -> list[str]:
        raise NotImplementedError
