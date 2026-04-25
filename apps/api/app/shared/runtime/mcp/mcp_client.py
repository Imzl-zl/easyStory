from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.modules.config_registry.schemas import McpServerConfig

from ..errors import ConfigurationError
from .mcp_endpoint_policy import validate_mcp_endpoint_url


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
        validate_mcp_endpoint_url(server.url)
        ClientSession, streamable_http_client = _load_mcp_sdk()
        async with httpx.AsyncClient(
            headers=dict(server.headers),
            timeout=server.timeout,
        ) as http_client:
            async with streamable_http_client(
                url=server.url,
                http_client=http_client,
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
        raise ConfigurationError("MCP content must be a list")
    return [_normalize_content_item(item) for item in value]


def _normalize_content_item(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    dumped = _dump_pydantic_model(item)
    if dumped is not None:
        return dumped
    raise ConfigurationError("MCP content item must be an object")


def _normalize_structured_content(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        dumped = _dump_pydantic_model(value)
        if dumped is None:
            raise ConfigurationError("MCP structuredContent must be an object")
        return dumped
    return value


def _dump_pydantic_model(value: Any) -> dict[str, Any] | None:
    model_dump = getattr(value, "model_dump", None)
    if model_dump is None:
        return None
    dumped = model_dump(by_alias=True, exclude_none=True)
    if not isinstance(dumped, dict):
        raise ConfigurationError("MCP model dump must be an object")
    return dumped


__all__ = [
    "McpToolCallResult",
    "McpToolCaller",
    "StreamableHttpMcpToolCaller",
]
