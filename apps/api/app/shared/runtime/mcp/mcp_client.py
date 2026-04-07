from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.config_registry.schemas import McpServerConfig

from ..errors import ConfigurationError


@dataclass(frozen=True)
class McpToolCallResult:
    content: list[dict[str, Any]]
    structured_content: dict[str, Any] | None
    is_error: bool


class McpToolCaller(Protocol):
    async def call_tool(
        self,
        *,
        server: McpServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolCallResult: ...


class StreamableHttpMcpToolCaller:
    async def call_tool(
        self,
        *,
        server: McpServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolCallResult:
        ClientSession, streamable_http_client = _load_mcp_sdk()
        async with streamable_http_client(
            url=server.url,
            headers=dict(server.headers),
            timeout=server.timeout,
        ) as transport:
            read_stream, write_stream, _ = transport
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments or {})
        return McpToolCallResult(
            content=_normalize_tool_content(getattr(result, "content", [])),
            structured_content=_normalize_structured_content(
                getattr(result, "structuredContent", None)
            ),
            is_error=bool(getattr(result, "isError", False)),
        )


def _load_mcp_sdk():
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except ImportError as exc:
        raise ConfigurationError(
            "MCP runtime requires the Python 'mcp' package to be installed"
        ) from exc
    return ClientSession, streamable_http_client


def _normalize_tool_content(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_structured_content(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ConfigurationError("MCP structuredContent must be an object")
    return value


__all__ = [
    "McpToolCallResult",
    "McpToolCaller",
    "StreamableHttpMcpToolCaller",
]
