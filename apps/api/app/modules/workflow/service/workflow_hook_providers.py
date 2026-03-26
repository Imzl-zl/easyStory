from __future__ import annotations

from typing import Any, Protocol

from app.shared.runtime import McpToolCaller, PluginRegistry, StreamableHttpMcpToolCaller
from app.shared.runtime.plugin_providers import (
    AgentPluginProvider,
    AsyncWebhookRequestSender,
    McpPluginProvider,
    ScriptPluginProvider,
    WebhookPluginProvider,
    WebhookResponse,
)

from .snapshot_support import load_mcp_server_snapshot
from .workflow_runtime_hook_support import HookExecutionContext

__all__ = ["WebhookResponse", "build_workflow_plugin_registry"]


class HookAgentRunner(Protocol):
    async def run_agent_hook(
        self,
        context: HookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any: ...


def build_workflow_plugin_registry(
    agent_runner: HookAgentRunner,
    *,
    webhook_request_sender: AsyncWebhookRequestSender | None = None,
    mcp_tool_caller: McpToolCaller | None = None,
) -> PluginRegistry:
    registry = PluginRegistry()
    registry.register("script", ScriptPluginProvider())
    registry.register(
        "webhook",
        WebhookPluginProvider(request_sender=webhook_request_sender),
    )
    registry.register("agent", AgentPluginProvider(agent_runner))
    registry.register(
        "mcp",
        McpPluginProvider(
            server_resolver=lambda context, server_id: load_mcp_server_snapshot(
                context.workflow.workflow_snapshot or {},
                server_id,
            ),
            tool_caller=mcp_tool_caller or StreamableHttpMcpToolCaller(),
        ),
    )
    return registry
