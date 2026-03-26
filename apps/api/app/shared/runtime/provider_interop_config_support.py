from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ConfigurationError
from .llm_protocol import normalize_http_header_name


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Provider interop config file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Provider interop config is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("provider interop config root must be an object")
    return payload


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prune_timestamps(timestamps: list[int], threshold: int) -> list[int]:
    return [timestamp for timestamp in timestamps if timestamp > threshold]


def _require_profile_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"provider interop field '{field_name}' must be a non-empty string")
    return value.strip()


def _optional_profile_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("provider interop optional string field must be a string")
    normalized = value.strip()
    return normalized or None


def _optional_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigurationError("provider interop rate limit must be a positive integer")
    return value


def _optional_profile_headers(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ConfigurationError("provider interop extra_headers must be an object")
    normalized: dict[str, str] = {}
    for raw_name, raw_value in value.items():
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            raise ConfigurationError("provider interop extra_headers must be a string mapping")
        header_name = normalize_http_header_name(raw_name)
        if header_name is None:
            raise ConfigurationError("provider interop extra_headers keys must be valid HTTP header names")
        header_value = raw_value.strip()
        if not header_value:
            raise ConfigurationError("provider interop extra_headers values must be non-empty strings")
        normalized[header_name] = header_value
    return normalized or None


def _to_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)
