from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
import hashlib
import json

from .assistant_tool_runtime_dto import AssistantToolDescriptor


def build_tool_catalog_version(
    descriptors: Iterable[AssistantToolDescriptor],
) -> str:
    serialized = sorted(
        (asdict(item) for item in descriptors),
        key=lambda item: str(item["name"]),
    )
    digest = hashlib.sha256(
        json.dumps(
            serialized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"tool_catalog:{digest}"
