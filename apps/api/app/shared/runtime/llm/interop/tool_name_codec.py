from __future__ import annotations

import hashlib
import re
from typing import Iterable, Literal, Mapping

ToolNamePolicy = Literal["passthrough", "safe_ascii_only"]

MAX_EXTERNAL_TOOL_NAME_LENGTH = 64
HASH_LENGTH = 8
HASH_SEPARATOR = "__"
SAFE_TOOL_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def build_tool_name_aliases(
    tool_names: Iterable[str],
    *,
    policy: ToolNamePolicy,
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    used_aliases: dict[str, str] = {}
    for canonical_name in sorted(_iter_unique_tool_names(tool_names)):
        alias = _build_external_tool_name_alias(
            canonical_name,
            policy=policy,
            used_aliases=used_aliases,
        )
        aliases[canonical_name] = alias
        used_aliases[alias] = canonical_name
    return aliases


def encode_tool_name(
    tool_name: str,
    *,
    tool_name_aliases: Mapping[str, str],
    policy: ToolNamePolicy,
) -> str:
    normalized_name = tool_name.strip()
    if not normalized_name:
        return normalized_name
    alias = tool_name_aliases.get(normalized_name)
    if alias is not None:
        return alias
    return _build_external_tool_name_alias(
        normalized_name,
        policy=policy,
        used_aliases={alias: canonical for canonical, alias in tool_name_aliases.items()},
    )


def decode_tool_name(
    tool_name: str,
    *,
    tool_name_aliases: Mapping[str, str],
) -> str:
    normalized_name = tool_name.strip()
    if not normalized_name:
        return normalized_name
    for canonical_name, alias in tool_name_aliases.items():
        if alias == normalized_name:
            return canonical_name
    return normalized_name


def _iter_unique_tool_names(tool_names: Iterable[str]) -> set[str]:
    normalized_names: set[str] = set()
    for tool_name in tool_names:
        stripped = tool_name.strip()
        if stripped:
            normalized_names.add(stripped)
    return normalized_names


def _build_external_tool_name_alias(
    canonical_name: str,
    *,
    policy: ToolNamePolicy,
    used_aliases: Mapping[str, str],
) -> str:
    if policy == "passthrough":
        return canonical_name
    base_alias = _build_safe_ascii_alias(canonical_name)
    candidate = _limit_alias_length(base_alias, canonical_name)
    if candidate not in used_aliases or used_aliases[candidate] == canonical_name:
        return candidate
    return _build_hashed_alias(base_alias, canonical_name)


def _build_safe_ascii_alias(tool_name: str) -> str:
    normalized = SAFE_TOOL_NAME_PATTERN.sub("_", tool_name.strip()).strip("_")
    if normalized:
        return normalized
    return "tool"


def _limit_alias_length(alias: str, canonical_name: str) -> str:
    if len(alias) <= MAX_EXTERNAL_TOOL_NAME_LENGTH:
        return alias
    return _build_hashed_alias(alias, canonical_name)


def _build_hashed_alias(alias: str, canonical_name: str) -> str:
    digest = hashlib.sha1(canonical_name.encode("utf-8")).hexdigest()[:HASH_LENGTH]
    prefix_budget = MAX_EXTERNAL_TOOL_NAME_LENGTH - len(HASH_SEPARATOR) - len(digest)
    prefix = alias[:prefix_budget].rstrip("_-")
    if not prefix:
        prefix = "tool"
    return f"{prefix}{HASH_SEPARATOR}{digest}"
