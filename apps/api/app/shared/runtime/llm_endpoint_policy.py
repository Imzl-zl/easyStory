from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

from app.shared.settings import (
    ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV,
    ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
    get_settings,
)

from .errors import ConfigurationError

PUBLIC_ENDPOINT_SCHEMES = frozenset({"https"})
PRIVATE_ENDPOINT_SCHEMES = frozenset({"http", "https"})
PRIVATE_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "host.docker.internal",
    }
)
PRIVATE_HOSTNAME_SUFFIXES = (".localhost", ".local")


def normalize_custom_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    normalized = base_url.strip()
    if not normalized:
        return None
    _validate_custom_base_url(normalized)
    return normalized


def _validate_custom_base_url(base_url: str) -> None:
    parsed = urlsplit(base_url)
    hostname = _validate_url_structure(parsed, base_url)
    if _is_private_hostname(hostname):
        _validate_private_endpoint(parsed.scheme)
        return
    _validate_public_endpoint(parsed.scheme)


def _validate_url_structure(parsed, base_url: str) -> str:
    if parsed.scheme not in PRIVATE_ENDPOINT_SCHEMES or not parsed.netloc:
        raise ConfigurationError("base_url must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise ConfigurationError("base_url must not include embedded credentials")
    if parsed.query or parsed.fragment:
        raise ConfigurationError("base_url must not include query parameters or fragments")
    if parsed.hostname is None:
        raise ConfigurationError(f"base_url is missing hostname: {base_url}")
    return parsed.hostname.lower()


def _validate_private_endpoint(scheme: str) -> None:
    if not get_settings().allow_private_model_endpoints:
        raise ConfigurationError(
            "Private or local model endpoints are disabled. "
            f"Set {ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV}=true to allow them."
        )
    if scheme not in PRIVATE_ENDPOINT_SCHEMES:
        raise ConfigurationError("base_url for private model endpoints must use http or https")


def _validate_public_endpoint(scheme: str) -> None:
    if scheme in PUBLIC_ENDPOINT_SCHEMES:
        return
    if scheme != "http":
        raise ConfigurationError("base_url for public model endpoints must use https")
    if get_settings().allow_insecure_public_model_endpoints:
        return
    raise ConfigurationError(
        "Public http model endpoints are disabled. "
        f"Set {ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV}=true to allow them."
    )


def _is_private_hostname(hostname: str) -> bool:
    if hostname in PRIVATE_HOSTNAMES:
        return True
    if hostname.endswith(PRIVATE_HOSTNAME_SUFFIXES):
        return True
    try:
        address = ip_address(hostname)
    except ValueError:
        return False
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )
