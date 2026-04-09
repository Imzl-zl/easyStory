from __future__ import annotations

from typing import Any

from ...errors import ConfigurationError


def require_list(
    value: Any,
    field_name: str,
    *,
    allow_none: bool = False,
) -> list[Any] | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"{field_name} must be a non-empty list")
    return value


def require_dict(
    value: Any,
    field_name: str,
    *,
    allow_none: bool = False,
) -> dict[str, Any] | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, dict):
        raise ConfigurationError(f"{field_name} must be an object")
    return value


def optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
