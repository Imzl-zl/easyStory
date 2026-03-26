"""Shared runtime contracts."""

from .errors import BudgetExceededError, ConfigurationError, EasyStoryError, UnknownModelError

__all__ = [
    "BudgetExceededError",
    "ConfigurationError",
    "EasyStoryError",
    "EXPORT_ROOT_DIR",
    "LLMToolProvider",
    "McpToolCaller",
    "McpToolCallResult",
    "ModelPrice",
    "ModelPricing",
    "PluginRegistry",
    "StreamableHttpMcpToolCaller",
    "SkillTemplateRenderer",
    "TokenCounter",
    "ToolProvider",
    "UnknownModelError",
]


def __getattr__(name: str):
    if name == "EXPORT_ROOT_DIR":
        from .storage_paths import EXPORT_ROOT_DIR

        return EXPORT_ROOT_DIR
    if name == "LLMToolProvider":
        from .llm_tool_provider import LLMToolProvider

        return LLMToolProvider
    if name == "McpToolCallResult":
        from .mcp_client import McpToolCallResult

        return McpToolCallResult
    if name == "McpToolCaller":
        from .mcp_client import McpToolCaller

        return McpToolCaller
    if name == "ModelPrice":
        from .token_counter import ModelPrice

        return ModelPrice
    if name == "ModelPricing":
        from .token_counter import ModelPricing

        return ModelPricing
    if name == "PluginRegistry":
        from .plugin_registry import PluginRegistry

        return PluginRegistry
    if name == "StreamableHttpMcpToolCaller":
        from .mcp_client import StreamableHttpMcpToolCaller

        return StreamableHttpMcpToolCaller
    if name == "SkillTemplateRenderer":
        from .template_renderer import SkillTemplateRenderer

        return SkillTemplateRenderer
    if name == "TokenCounter":
        from .token_counter import TokenCounter

        return TokenCounter
    if name == "ToolProvider":
        from .tool_provider import ToolProvider

        return ToolProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
