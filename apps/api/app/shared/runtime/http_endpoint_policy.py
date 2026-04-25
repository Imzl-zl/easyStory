from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlsplit

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


@dataclass(frozen=True)
class HttpEndpointPolicy:
    field_name: str
    endpoint_subject: str
    allow_private_endpoints: bool
    allow_private_endpoints_env: str
    allow_insecure_public_http: bool
    allow_insecure_public_http_env: str


def validate_http_endpoint_url(url: str, policy: HttpEndpointPolicy) -> None:
    parsed = urlsplit(url)
    hostname = _validate_url_structure(parsed, url, policy.field_name)
    if _is_private_hostname(hostname):
        _validate_private_endpoint(parsed.scheme, policy)
        return
    _validate_public_endpoint(parsed.scheme, policy)


def _validate_url_structure(parsed, url: str, field_name: str) -> str:
    if parsed.scheme not in PRIVATE_ENDPOINT_SCHEMES or not parsed.netloc:
        raise ConfigurationError(f"{field_name} must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise ConfigurationError(f"{field_name} must not include embedded credentials")
    if parsed.query or parsed.fragment:
        raise ConfigurationError(
            f"{field_name} must not include query parameters or fragments"
        )
    if parsed.hostname is None:
        raise ConfigurationError(f"{field_name} is missing hostname: {url}")
    return parsed.hostname.lower()


def _validate_private_endpoint(scheme: str, policy: HttpEndpointPolicy) -> None:
    if not policy.allow_private_endpoints:
        raise ConfigurationError(
            f"Private or local {policy.endpoint_subject} are disabled. "
            f"Set {policy.allow_private_endpoints_env}=true to allow them."
        )
    if scheme not in PRIVATE_ENDPOINT_SCHEMES:
        raise ConfigurationError(
            f"{policy.field_name} for private {policy.endpoint_subject} must use http or https"
        )


def _validate_public_endpoint(scheme: str, policy: HttpEndpointPolicy) -> None:
    if scheme in PUBLIC_ENDPOINT_SCHEMES:
        return
    if scheme != "http":
        raise ConfigurationError(
            f"{policy.field_name} for public {policy.endpoint_subject} must use https"
        )
    if policy.allow_insecure_public_http:
        return
    raise ConfigurationError(
        f"Public http {policy.endpoint_subject} are disabled. "
        f"Set {policy.allow_insecure_public_http_env}=true to allow them."
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


__all__ = ["HttpEndpointPolicy", "validate_http_endpoint_url"]
