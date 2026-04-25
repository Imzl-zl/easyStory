from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from mcp.types import TextContent

from app.modules.config_registry.schemas import McpServerConfig
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.mcp import mcp_client
from app.shared.runtime.mcp.mcp_client import StreamableHttpMcpToolCaller


def test_normalize_tool_content_preserves_sdk_content_models() -> None:
    content = mcp_client._normalize_tool_content(
        [TextContent(type="text", text="hello")]
    )

    assert content == [{"type": "text", "text": "hello"}]


def test_normalize_tool_content_rejects_unknown_item_type() -> None:
    with pytest.raises(ConfigurationError, match="content item must be an object"):
        mcp_client._normalize_tool_content([object()])


async def test_streamable_http_tool_caller_uses_sdk_http_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeHttpClient:
        def __init__(self, *, headers, timeout):
            captured["headers"] = headers
            captured["timeout"] = timeout

        async def __aenter__(self):
            captured["http_client"] = self
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class FakeClientSession:
        def __init__(self, read_stream, write_stream):
            captured["session_streams"] = (read_stream, write_stream)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def initialize(self) -> None:
            captured["initialized"] = True

        async def call_tool(self, tool_name: str, arguments: dict):
            captured["tool_call"] = (tool_name, arguments)
            return SimpleNamespace(
                content=[TextContent(type="text", text="ok")],
                structuredContent={"status": "done"},
                isError=False,
            )

    @asynccontextmanager
    async def fake_streamable_http_client(*, url, http_client):
        captured["url"] = url
        captured["sdk_http_client"] = http_client
        yield "read", "write", lambda: "session-id"

    monkeypatch.setattr(mcp_client.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(
        mcp_client,
        "_load_mcp_sdk",
        lambda: (FakeClientSession, fake_streamable_http_client),
    )

    result = await StreamableHttpMcpToolCaller().call_tool(
        server=McpServerConfig(
            id="mcp.test",
            name="Test MCP",
            url="https://example.com/mcp",
            headers={"X-Test": "demo"},
            timeout=45,
        ),
        tool_name="search",
        arguments={"query": "hello"},
    )

    assert captured["headers"] == {"X-Test": "demo"}
    assert captured["timeout"] == 45
    assert captured["url"] == "https://example.com/mcp"
    assert captured["sdk_http_client"] is captured["http_client"]
    assert captured["initialized"] is True
    assert captured["tool_call"] == ("search", {"query": "hello"})
    assert result.content == [{"type": "text", "text": "ok"}]
    assert result.structured_content == {"status": "done"}
    assert result.is_error is False
