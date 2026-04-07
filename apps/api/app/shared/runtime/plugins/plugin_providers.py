from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import inspect
from typing import Any, Callable, Protocol

import httpx

from app.modules.config_registry.schemas.hook_action_config import (
    AgentHookConfig,
    McpHookConfig,
    ScriptHookConfig,
    WebhookHookConfig,
)

from ..errors import ConfigurationError
from ..mcp.mcp_client import McpToolCaller


class AgentPluginRunner(Protocol):
    async def run_agent_hook(
        self,
        context: Any,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any: ...


class AsyncWebhookRequestSender(Protocol):
    async def __call__(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        json_body: Any,
    ) -> "WebhookResponse": ...


@dataclass(frozen=True)
class WebhookResponse:
    status_code: int
    json_body: dict[str, Any] | None
    text: str


class ScriptPluginProvider:
    async def execute(self, *, config: dict[str, Any], context: Any) -> Any:
        typed = ScriptHookConfig.model_validate(config)
        handler = _resolve_handler(typed.module, typed.function)
        result = handler(context, dict(typed.params))
        if inspect.isawaitable(result):
            return await result
        return result


class WebhookPluginProvider:
    def __init__(self, *, request_sender: AsyncWebhookRequestSender | None = None) -> None:
        self.request_sender = request_sender or _default_webhook_request_sender

    async def execute(self, *, config: dict[str, Any], context: Any) -> Any:
        typed = WebhookHookConfig.model_validate(config)
        body = context.payload if typed.body is None else typed.body
        response = await self.request_sender(
            method=typed.method,
            url=typed.url,
            headers=dict(typed.headers),
            json_body=body,
        )
        if response.status_code >= 400:
            raise RuntimeError(_build_webhook_error_message(response))
        return {
            "status_code": response.status_code,
            "json_body": response.json_body,
            "text": response.text,
        }


class AgentPluginProvider:
    def __init__(self, runner: AgentPluginRunner) -> None:
        self.runner = runner

    async def execute(self, *, config: dict[str, Any], context: Any) -> Any:
        typed = AgentHookConfig.model_validate(config)
        return await self.runner.run_agent_hook(
            context,
            agent_id=typed.agent_id,
            input_mapping=dict(typed.input_mapping),
        )


class McpPluginProvider:
    def __init__(
        self,
        *,
        server_resolver: Callable[[Any, str], Any],
        tool_caller: McpToolCaller,
    ) -> None:
        self.server_resolver = server_resolver
        self.tool_caller = tool_caller

    async def execute(self, *, config: dict[str, Any], context: Any) -> Any:
        typed = McpHookConfig.model_validate(config)
        arguments = dict(typed.arguments)
        for target, source in typed.input_mapping.items():
            arguments[target] = context.read_path(source)
        server = self.server_resolver(context, typed.server_id)
        _require_enabled_mcp_server(server)
        result = await self.tool_caller.call_tool(
            server=server,
            tool_name=typed.tool_name,
            arguments=arguments,
        )
        _raise_for_mcp_tool_error(server.id, typed.tool_name, result.content, result.structured_content, result.is_error)
        return {
            "content": result.content,
            "structured_content": result.structured_content,
            "is_error": result.is_error,
        }


def _resolve_handler(module_name: str, function_name: str):
    module = import_module(module_name)
    try:
        handler = getattr(module, function_name)
    except AttributeError as exc:
        raise RuntimeError(
            f"Hook function not found: {module_name}.{function_name}"
        ) from exc
    if not callable(handler):
        raise RuntimeError(f"Hook target is not callable: {module_name}.{function_name}")
    return handler


def _build_webhook_error_message(response: WebhookResponse) -> str:
    if response.json_body is not None and isinstance(response.json_body.get("error"), str):
        return f"Webhook hook failed: HTTP {response.status_code} - {response.json_body['error']}"
    suffix = response.text.strip()
    if suffix:
        return f"Webhook hook failed: HTTP {response.status_code} - {suffix}"
    return f"Webhook hook failed: HTTP {response.status_code}"


def _require_enabled_mcp_server(server: Any) -> None:
    if getattr(server, "enabled", True):
        return
    server_id = getattr(server, "id", "<unknown>")
    raise ConfigurationError(f"MCP server '{server_id}' is disabled")


def _raise_for_mcp_tool_error(
    server_id: str,
    tool_name: str,
    content: list[dict[str, Any]],
    structured_content: dict[str, Any] | None,
    is_error: bool,
) -> None:
    if not is_error:
        return
    message = f"MCP hook failed: server '{server_id}' tool '{tool_name}' returned is_error=true"
    detail = _extract_mcp_error_detail(content, structured_content)
    if detail:
        message = f"{message} - {detail}"
    raise RuntimeError(message)


def _extract_mcp_error_detail(
    content: list[dict[str, Any]],
    structured_content: dict[str, Any] | None,
) -> str | None:
    if structured_content is not None:
        for key in ("error", "message", "detail"):
            value = structured_content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    texts = [
        item["text"].strip()
        for item in content
        if isinstance(item.get("text"), str) and item["text"].strip()
    ]
    if texts:
        return " ".join(texts)
    return None


async def _default_webhook_request_sender(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: Any,
) -> WebhookResponse:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
        )
    return WebhookResponse(
        status_code=response.status_code,
        json_body=_read_json_body(response),
        text=response.text,
    )


def _read_json_body(response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


__all__ = [
    "AgentPluginProvider",
    "AgentPluginRunner",
    "AsyncWebhookRequestSender",
    "McpPluginProvider",
    "ScriptPluginProvider",
    "WebhookPluginProvider",
    "WebhookResponse",
]
