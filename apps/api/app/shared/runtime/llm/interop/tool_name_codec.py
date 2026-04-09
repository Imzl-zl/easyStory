from __future__ import annotations

import hashlib
import re
from typing import Iterable, Literal, Mapping

ToolNamePolicy = Literal["passthrough", "safe_ascii_only"]

MAX_EXTERNAL_TOOL_NAME_LENGTH = 64
HASH_LENGTH = 8
HASH_SEPARATOR = "__"
SAFE_TOOL_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")
_MISSING = object()


class ToolNameAliasMap(dict[str, str]):
    __slots__ = ("_reverse_aliases",)

    def __init__(self, aliases: Mapping[str, str] | None = None) -> None:
        super().__init__(aliases or {})
        self._reverse_aliases: dict[str, str] | None = None

    @property
    def reverse_aliases(self) -> dict[str, str]:
        if self._reverse_aliases is None:
            self._reverse_aliases = _build_reverse_alias_lookup(self)
        return self._reverse_aliases

    def __setitem__(self, key: str, value: str) -> None:
        self._reverse_aliases = None
        super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        self._reverse_aliases = None
        super().__delitem__(key)

    def clear(self) -> None:
        self._reverse_aliases = None
        super().clear()

    def pop(self, key: str, default: object = _MISSING) -> object:
        if key in self:
            self._reverse_aliases = None
            return super().pop(key)
        if default is _MISSING:
            return super().pop(key)
        return default

    def popitem(self) -> tuple[str, str]:
        self._reverse_aliases = None
        return super().popitem()

    def setdefault(self, key: str, default: object = _MISSING) -> object:
        if key in self:
            return self[key]
        self._reverse_aliases = None
        if default is _MISSING:
            return super().setdefault(key)
        return super().setdefault(key, default)

    def update(self, *args: object, **kwargs: str) -> None:
        if args or kwargs:
            self._reverse_aliases = None
        super().update(*args, **kwargs)

    def __ior__(self, other: Mapping[str, str]) -> "ToolNameAliasMap":
        self._reverse_aliases = None
        super().__ior__(other)
        return self


def build_tool_name_aliases(
    tool_names: Iterable[str],
    *,
    policy: ToolNamePolicy,
) -> ToolNameAliasMap:
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
    alias_map = ToolNameAliasMap(aliases)
    _ = alias_map.reverse_aliases
    return alias_map


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
        used_aliases=_read_reverse_aliases(tool_name_aliases),
    )


def decode_tool_name(
    tool_name: str,
    *,
    tool_name_aliases: Mapping[str, str],
) -> str:
    normalized_name = tool_name.strip()
    if not normalized_name:
        return normalized_name
    reverse_aliases = _read_reverse_aliases(tool_name_aliases)
    return reverse_aliases.get(normalized_name, normalized_name)


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


def _read_reverse_aliases(tool_name_aliases: Mapping[str, str]) -> Mapping[str, str]:
    if isinstance(tool_name_aliases, ToolNameAliasMap):
        return tool_name_aliases.reverse_aliases
    return _build_reverse_alias_lookup(tool_name_aliases)


def _build_reverse_alias_lookup(
    tool_name_aliases: Mapping[str, str],
) -> dict[str, str]:
    return {alias: canonical_name for canonical_name, alias in tool_name_aliases.items()}
