from __future__ import annotations

from typing import Protocol

from app.modules.config_registry import ConfigLoader
from app.shared.runtime import McpToolCaller, PluginRegistry, StreamableHttpMcpToolCaller
from app.shared.runtime.plugin_providers import (
    AgentPluginProvider,
    AsyncWebhookRequestSender,
    McpPluginProvider,
    ScriptPluginProvider,
    WebhookPluginProvider,
)


class AssistantHookAgentRunner(Protocol):
    async def run_agent_hook(self, context, *, agent_id: str, input_mapping: dict[str, str]): ...


def build_assistant_plugin_registry(
    agent_runner: AssistantHookAgentRunner,
    *,
    config_loader: ConfigLoader,
    webhook_request_sender: AsyncWebhookRequestSender | None = None,
    mcp_tool_caller: McpToolCaller | None = None,
) -> PluginRegistry:
    registry = PluginRegistry()
    registry.register("script", ScriptPluginProvider())
    registry.register("webhook", WebhookPluginProvider(request_sender=webhook_request_sender))
    registry.register("agent", AgentPluginProvider(agent_runner))
    registry.register(
        "mcp",
        McpPluginProvider(
            server_resolver=lambda _context, server_id: config_loader.load_mcp_server(server_id),
            tool_caller=mcp_tool_caller or StreamableHttpMcpToolCaller(),
        ),
    )
    return registry
