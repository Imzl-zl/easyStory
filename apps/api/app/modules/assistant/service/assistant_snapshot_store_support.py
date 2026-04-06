from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import json
from typing import Any, Collection
import uuid

from app.shared.runtime.errors import ConfigurationError


def load_snapshot_object(path: Path, snapshot_label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"{snapshot_label} is not valid JSON: {path}") from exc
    if isinstance(payload, dict):
        return payload
    raise ConfigurationError(f"{snapshot_label} must be an object: {path}")


def dump_snapshot(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


@dataclass(frozen=True)
class SnapshotReader:
    snapshot_label: str
    path: Path
    quoted_field_name: bool = False
    normalize_datetimes_to_utc: bool = False

    def read_required_string(
        self,
        payload: dict[str, object],
        field_name: str,
        *,
        strip: bool = True,
    ) -> str:
        raw = payload.get(field_name)
        if not isinstance(raw, str):
            self._raise(field_name, "must be a non-empty string")
        value = raw.strip() if strip else raw
        if value:
            return value
        self._raise(field_name, "must be a non-empty string")

    def read_optional_string(
        self,
        payload: dict[str, object],
        field_name: str,
        *,
        strip: bool = True,
    ) -> str | None:
        raw = payload.get(field_name)
        if raw is None:
            return None
        if not isinstance(raw, str):
            self._raise(field_name, "must be a string or null")
        value = raw.strip() if strip else raw
        return value or None

    def read_required_literal_string(
        self,
        payload: dict[str, object],
        field_name: str,
        allowed_values: Collection[str],
        *,
        strip: bool = True,
    ) -> str:
        value = self.read_required_string(payload, field_name, strip=strip)
        if value in allowed_values:
            return value
        allowed = ", ".join(sorted(allowed_values))
        self._raise(field_name, f"must be one of [{allowed}]")

    def read_optional_literal_string(
        self,
        payload: dict[str, object],
        field_name: str,
        allowed_values: Collection[str],
        *,
        strip: bool = True,
    ) -> str | None:
        value = self.read_optional_string(payload, field_name, strip=strip)
        if value is None:
            return None
        if value in allowed_values:
            return value
        allowed = ", ".join(sorted(allowed_values))
        self._raise(field_name, f"must be one of [{allowed}]")

    def read_required_uuid(self, payload: dict[str, object], field_name: str) -> uuid.UUID:
        value = self.read_required_string(payload, field_name, strip=True)
        try:
            return uuid.UUID(value)
        except ValueError as exc:
            raise ConfigurationError(f"{self._field_ref(field_name)} must be a UUID: {self.path}") from exc

    def read_optional_uuid(self, payload: dict[str, object], field_name: str) -> uuid.UUID | None:
        value = self.read_optional_string(payload, field_name, strip=True)
        if value is None:
            return None
        try:
            return uuid.UUID(value)
        except ValueError as exc:
            raise ConfigurationError(
                f"{self._field_ref(field_name)} must be a UUID or null: {self.path}"
            ) from exc

    def read_required_int(self, payload: dict[str, object], field_name: str) -> int:
        value = payload.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int):
            self._raise(field_name, "must be an integer")
        return value

    def read_required_positive_int(self, payload: dict[str, object], field_name: str) -> int:
        value = self.read_required_int(payload, field_name)
        if value >= 1:
            return value
        self._raise(field_name, "must be >= 1")

    def read_optional_positive_int(self, payload: dict[str, object], field_name: str) -> int | None:
        value = payload.get(field_name)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            self._raise(field_name, "must be an integer or null")
        if value >= 1:
            return value
        self._raise(field_name, "must be >= 1 when provided")

    def read_optional_bool(self, payload: dict[str, object], field_name: str) -> bool | None:
        value = payload.get(field_name)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        self._raise(field_name, "must be a bool or null")

    def read_required_object(self, payload: dict[str, object], field_name: str) -> dict[str, Any]:
        value = payload.get(field_name)
        if isinstance(value, dict):
            return value
        self._raise(field_name, "must be an object")

    def read_optional_object(self, payload: dict[str, object], field_name: str) -> dict[str, Any] | None:
        value = payload.get(field_name)
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        self._raise(field_name, "must be an object or null")

    def read_optional_object_tuple(
        self,
        payload: dict[str, object],
        field_name: str,
    ) -> tuple[dict[str, Any], ...]:
        value = payload.get(field_name)
        if value is None:
            return ()
        if not isinstance(value, list):
            self._raise(field_name, "must be an array or null")
        normalized: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                self._raise(field_name, "entries must be objects")
            normalized.append(item)
        return tuple(normalized)

    def read_required_string_tuple(
        self,
        payload: dict[str, object],
        field_name: str,
        *,
        strip: bool = True,
    ) -> tuple[str, ...]:
        value = payload.get(field_name)
        if not isinstance(value, list):
            self._raise(field_name, "must be an array")
        return self._normalize_string_sequence(field_name, value, strip=strip)

    def read_optional_string_tuple(
        self,
        payload: dict[str, object],
        field_name: str,
        *,
        strip: bool = True,
    ) -> tuple[str, ...]:
        value = payload.get(field_name)
        if value is None:
            return ()
        if not isinstance(value, list):
            self._raise(field_name, "must be an array or null")
        return self._normalize_string_sequence(field_name, value, strip=strip)

    def read_string_map(
        self,
        payload: dict[str, object],
        field_name: str,
        *,
        strip: bool = True,
    ) -> dict[str, str]:
        value = payload.get(field_name)
        if not isinstance(value, dict):
            self._raise(field_name, "must be an object")
        normalized: dict[str, str] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key.strip():
                self._raise(field_name, "keys must be non-empty strings")
            if not isinstance(item, str):
                self._raise(field_name, "values must be non-empty strings")
            normalized_value = item.strip() if strip else item
            if not normalized_value:
                self._raise(field_name, "values must be non-empty strings")
            normalized[key] = normalized_value
        return normalized

    def read_required_datetime(self, payload: dict[str, object], field_name: str) -> datetime:
        raw = self.read_required_string(payload, field_name, strip=True)
        return self._parse_datetime(field_name, raw, optional=False)

    def read_optional_datetime(self, payload: dict[str, object], field_name: str) -> datetime | None:
        raw = self.read_optional_string(payload, field_name, strip=True)
        if raw is None:
            return None
        return self._parse_datetime(field_name, raw, optional=True)

    def _parse_datetime(self, field_name: str, raw: str, *, optional: bool) -> datetime:
        try:
            value = datetime.fromisoformat(raw)
        except ValueError as exc:
            expectation = "must be ISO datetime or null" if optional else "must be ISO datetime"
            raise ConfigurationError(f"{self._field_ref(field_name)} {expectation}: {self.path}") from exc
        if not self.normalize_datetimes_to_utc:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _normalize_string_sequence(
        self,
        field_name: str,
        values: list[object],
        *,
        strip: bool,
    ) -> tuple[str, ...]:
        normalized: list[str] = []
        for item in values:
            if not isinstance(item, str):
                self._raise(field_name, "entries must be non-empty strings")
            normalized_item = item.strip() if strip else item
            if not normalized_item:
                self._raise(field_name, "entries must be non-empty strings")
            normalized.append(normalized_item)
        return tuple(normalized)

    def _field_ref(self, field_name: str) -> str:
        if self.quoted_field_name:
            return f"{self.snapshot_label} field '{field_name}'"
        return f"{self.snapshot_label} {field_name}"

    def _raise(self, field_name: str, expectation: str) -> None:
        raise ConfigurationError(f"{self._field_ref(field_name)} {expectation}: {self.path}")
