from __future__ import annotations

from app.shared.settings import (
    ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV,
    ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
    get_settings,
)

from ..http_endpoint_policy import HttpEndpointPolicy, validate_http_endpoint_url


def normalize_custom_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    normalized = base_url.strip()
    if not normalized:
        return None
    _validate_custom_base_url(normalized)
    return normalized


def _validate_custom_base_url(base_url: str) -> None:
    settings = get_settings()
    validate_http_endpoint_url(
        base_url,
        HttpEndpointPolicy(
            field_name="base_url",
            endpoint_subject="model endpoints",
            allow_private_endpoints=settings.allow_private_model_endpoints,
            allow_private_endpoints_env=ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
            allow_insecure_public_http=settings.allow_insecure_public_model_endpoints,
            allow_insecure_public_http_env=ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV,
        ),
    )
