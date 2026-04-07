from __future__ import annotations

from typing import Any, Callable, Protocol

from app.modules.config_registry import ConfigLoader
from app.shared.runtime import McpToolCaller, PluginRegistry, StreamableHttpMcpToolCaller
from app.shared.runtime.plugins.plugin_providers import (
    AgentPluginProvider,
    AsyncWebhookRequestSender,
    McpPluginProvider,
    ScriptPluginProvider,
    WebhookPluginProvider,
)


class AssistantHookAgentRunner(Protocol):
    async def run_agent_hook(self, context, *, agent_id: str, input_mapping: dict[str, str]): ...


AssistantMcpServerResolver = Callable[[Any, str], Any]


def _build_config_loader_resolver(config_loader: ConfigLoader) -> AssistantMcpServerResolver:
    def resolve(_context: Any, server_id: str):
        return config_loader.load_mcp_server(server_id)

    return resolve


def build_assistant_plugin_registry(
    agent_runner: AssistantHookAgentRunner,
    *,
    mcp_server_resolver: AssistantMcpServerResolver | None = None,
    config_loader: ConfigLoader | None = None,
    webhook_request_sender: AsyncWebhookRequestSender | None = None,
    mcp_tool_caller: McpToolCaller | None = None,
) -> PluginRegistry:
    if mcp_server_resolver is None:
        if config_loader is None:
            raise ValueError("Either mcp_server_resolver or config_loader must be provided")
        mcp_server_resolver = _build_config_loader_resolver(config_loader)
    registry = PluginRegistry()
    registry.register("script", ScriptPluginProvider())
    registry.register("webhook", WebhookPluginProvider(request_sender=webhook_request_sender))
    registry.register("agent", AgentPluginProvider(agent_runner))
    registry.register(
        "mcp",
        McpPluginProvider(
            server_resolver=mcp_server_resolver,
            tool_caller=mcp_tool_caller or StreamableHttpMcpToolCaller(),
        ),
    )
    return registry
