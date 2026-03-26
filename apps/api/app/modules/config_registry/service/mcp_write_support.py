from __future__ import annotations

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import McpServerConfig
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError, NotFoundError

from .mcp_query_dto import McpServerConfigUpdateDTO
from .write_validation_support import validate_config_model


def build_mcp_server_config(payload: McpServerConfigUpdateDTO) -> McpServerConfig:
    document = payload.model_dump()
    document.pop("author", None)
    return validate_config_model(McpServerConfig, document)


def ensure_matching_mcp_server_id(path_server_id: str, payload_server_id: str) -> None:
    if payload_server_id != path_server_id:
        raise BusinessRuleError(
            f"MCP server payload id '{payload_server_id}' does not match path '{path_server_id}'"
        )


def require_mcp_server(config_loader: ConfigLoader, server_id: str) -> McpServerConfig:
    try:
        return config_loader.load_mcp_server(server_id)
    except ConfigurationError as exc:
        if str(exc) == f"MCP server not found: {server_id}":
            raise NotFoundError(str(exc)) from exc
        raise


def serialize_mcp_server_document(server: McpServerConfig) -> dict[str, object]:
    return server.model_dump(
        exclude_defaults=True,
        exclude_none=True,
    )
