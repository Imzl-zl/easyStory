from __future__ import annotations

from app.shared.settings import (
    ALLOW_INSECURE_PUBLIC_MCP_ENDPOINTS_ENV,
    ALLOW_PRIVATE_MCP_ENDPOINTS_ENV,
    get_settings,
)

from ..errors import ConfigurationError
from ..http_endpoint_policy import HttpEndpointPolicy, validate_http_endpoint_url


def validate_mcp_endpoint_url(url: str) -> None:
    settings = get_settings()
    validate_http_endpoint_url(
        url,
        HttpEndpointPolicy(
            field_name="MCP url",
            endpoint_subject="MCP endpoints",
            allow_private_endpoints=settings.allow_private_mcp_endpoints,
            allow_private_endpoints_env=ALLOW_PRIVATE_MCP_ENDPOINTS_ENV,
            allow_insecure_public_http=settings.allow_insecure_public_mcp_endpoints,
            allow_insecure_public_http_env=ALLOW_INSECURE_PUBLIC_MCP_ENDPOINTS_ENV,
        ),
    )


def normalize_mcp_endpoint_url(url: str) -> str:
    normalized = url.strip()
    if not normalized:
        raise ConfigurationError("MCP 地址不能为空。")
    validate_mcp_endpoint_url(normalized)
    return normalized


__all__ = ["normalize_mcp_endpoint_url", "validate_mcp_endpoint_url"]
