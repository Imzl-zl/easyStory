from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TRUSTED_ACTIVE_BUFFER_SOURCE = "studio_editor"


@dataclass(frozen=True)
class TrustedProjectDocumentBufferSnapshot:
    base_version: str
    buffer_hash: str
    source: str


def build_project_document_buffer_hash(content: str) -> str:
    hash_value = 0xCBF29CE484222325
    for character in content:
        hash_value ^= ord(character)
        hash_value = (hash_value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"fnv1a64:{hash_value:016x}"


def extract_trusted_project_document_buffer_snapshot(
    active_buffer_state: dict[str, Any] | None,
) -> TrustedProjectDocumentBufferSnapshot | None:
    if not isinstance(active_buffer_state, dict):
        return None
    if active_buffer_state.get("dirty") is not False:
        return None
    base_version = _read_non_empty_string(active_buffer_state.get("base_version"))
    buffer_hash = _read_non_empty_string(active_buffer_state.get("buffer_hash"))
    source = _read_non_empty_string(active_buffer_state.get("source"))
    if base_version is None or buffer_hash is None:
        return None
    if source != TRUSTED_ACTIVE_BUFFER_SOURCE:
        return None
    return TrustedProjectDocumentBufferSnapshot(
        base_version=base_version,
        buffer_hash=buffer_hash,
        source=source,
    )


def _read_non_empty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
