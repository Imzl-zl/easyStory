from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.shared.runtime.llm_protocol import LLMContinuationSupport
from app.shared.runtime.token_counter import TokenCounter

from ..context.assistant_input_budget_support import (
    estimate_assistant_request_tokens,
    trim_text_to_token_budget,
)
from ..assistant_run_budget import AssistantRunBudget
from ..assistant_runtime_terminal import AssistantRuntimeTerminalError
from ..dto import AssistantContinuationCompactionSnapshotDTO

TOOL_RESULT_TEXT_KEYS = frozenset({"content", "text", "message"})


def apply_tool_loop_request_budget(
    *,
    prompt: str,
    system_prompt: str | None,
    tool_schemas: list[dict[str, Any]],
    continuation_items: tuple[dict[str, Any], ...],
    provider_continuation_state: dict[str, Any] | None,
    continuation_support: LLMContinuationSupport,
    run_budget: AssistantRunBudget,
    token_counter: TokenCounter | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None]:
    max_input_tokens = run_budget.max_input_tokens
    request_items = _resolve_request_continuation_items(
        continuation_items=continuation_items,
        provider_continuation_state=provider_continuation_state,
        continuation_support=continuation_support,
    )
    if max_input_tokens is None:
        return request_items, _replace_latest_items(provider_continuation_state, request_items), None
    counter = token_counter or TokenCounter()
    estimated_tokens = estimate_assistant_request_tokens(
        prompt=prompt,
        system_prompt=system_prompt,
        tools=tool_schemas,
        continuation_items=request_items,
        continuation_support=continuation_support,
        provider_continuation_state=provider_continuation_state,
        token_counter=counter,
    )
    if estimated_tokens <= max_input_tokens:
        return request_items, _replace_latest_items(provider_continuation_state, request_items), None
    if not request_items:
        raise _build_budget_exhausted_error()
    compacted_items = _compact_continuation_items(
        request_items,
        target_tokens=max_input_tokens,
        prompt=prompt,
        system_prompt=system_prompt,
        tool_schemas=tool_schemas,
        continuation_support=continuation_support,
        provider_continuation_state=provider_continuation_state,
        token_counter=counter,
    )
    compacted_state = _replace_latest_items(provider_continuation_state, compacted_items)
    estimated_compacted_tokens = estimate_assistant_request_tokens(
        prompt=prompt,
        system_prompt=system_prompt,
        tools=tool_schemas,
        continuation_items=compacted_items,
        continuation_support=continuation_support,
        provider_continuation_state=compacted_state,
        token_counter=counter,
    )
    if estimated_compacted_tokens > max_input_tokens:
        raise _build_budget_exhausted_error()
    return (
        compacted_items,
        compacted_state,
        _build_continuation_compaction_snapshot(
            original_items=request_items,
            compacted_items=compacted_items,
            budget_limit_tokens=max_input_tokens,
            estimated_tokens_before=estimated_tokens,
            estimated_tokens_after=estimated_compacted_tokens,
            token_counter=counter,
        ),
    )


def _resolve_request_continuation_items(
    *,
    continuation_items: tuple[dict[str, Any], ...],
    provider_continuation_state: dict[str, Any] | None,
    continuation_support: LLMContinuationSupport,
) -> list[dict[str, Any]]:
    if (
        continuation_support.continuation_mode != "runtime_replay"
        and isinstance(provider_continuation_state, dict)
    ):
        latest_items = provider_continuation_state.get("latest_items")
        if isinstance(latest_items, list):
            return [item for item in latest_items if isinstance(item, dict)]
    return [item for item in continuation_items if isinstance(item, dict)]


def _compact_continuation_items(
    items: list[dict[str, Any]],
    *,
    target_tokens: int,
    prompt: str,
    system_prompt: str | None,
    tool_schemas: list[dict[str, Any]],
    continuation_support: LLMContinuationSupport,
    provider_continuation_state: dict[str, Any] | None,
    token_counter: TokenCounter,
) -> list[dict[str, Any]]:
    compacted = [_normalize_continuation_item(item) for item in deepcopy(items)]
    while True:
        estimated_tokens = estimate_assistant_request_tokens(
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tool_schemas,
            continuation_items=compacted,
            continuation_support=continuation_support,
            provider_continuation_state=_replace_latest_items(provider_continuation_state, compacted),
            token_counter=token_counter,
        )
        if estimated_tokens <= target_tokens:
            return compacted
        slot_path = _find_largest_text_slot(compacted, token_counter=token_counter)
        if slot_path is None:
            reduced = _drop_redundant_content_items(compacted)
            if reduced == compacted:
                return compacted
            compacted = reduced
            continue
        current_text = _read_path(compacted, slot_path)
        if not isinstance(current_text, str) or not current_text.strip():
            reduced = _drop_redundant_content_items(compacted)
            if reduced == compacted:
                return compacted
            compacted = reduced
            continue
        current_tokens = token_counter.count(current_text, "default")
        next_budget = max(1, current_tokens // 2)
        trimmed_text = trim_text_to_token_budget(
            current_text,
            target_tokens=next_budget,
            token_counter=token_counter,
        )
        if trimmed_text == current_text:
            reduced = _drop_redundant_content_items(compacted)
            if reduced == compacted:
                return compacted
            compacted = reduced
            continue
        _write_path(compacted, slot_path, trimmed_text)


def _normalize_continuation_item(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("item_type") != "tool_result":
        return item
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return item
    normalized = dict(item)
    tool_name = payload.get("tool_name") or item.get("tool_name")
    if tool_name == "project.read_documents":
        normalized["payload"] = _normalize_read_documents_payload(payload)
        return normalized
    if tool_name == "project.search_documents":
        normalized["payload"] = _normalize_search_documents_payload(payload)
        return normalized
    if tool_name == "project.list_documents":
        normalized["payload"] = _normalize_list_documents_payload(payload)
        return normalized
    return normalized


def _normalize_read_documents_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    structured_output = payload.get("structured_output")
    if not isinstance(structured_output, dict):
        return normalized
    documents = structured_output.get("documents")
    errors = structured_output.get("errors")
    normalized["structured_output"] = {
        "documents": [
            {
                key: item.get(key)
                for key in (
                    "path",
                    "document_ref",
                    "version",
                    "truncated",
                    "next_cursor",
                    "schema_id",
                    "content",
                )
                if item.get(key) is not None
            }
            for item in documents
            if isinstance(item, dict)
        ],
        "errors": [
            {
                key: item.get(key)
                for key in ("path", "code", "message")
                if item.get(key) is not None
            }
            for item in errors
            if isinstance(item, dict)
        ],
        "catalog_version": structured_output.get("catalog_version"),
    }
    return normalized


def _normalize_list_documents_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    structured_output = payload.get("structured_output")
    if not isinstance(structured_output, dict):
        return normalized
    documents = structured_output.get("documents")
    normalized["structured_output"] = {
        "documents": [
            {
                key: item.get(key)
                for key in (
                    "path",
                    "document_ref",
                    "source",
                    "document_kind",
                    "schema_id",
                    "content_state",
                    "writable",
                    "version",
                )
                if item.get(key) is not None
            }
            for item in documents
            if isinstance(item, dict)
        ],
        "catalog_version": structured_output.get("catalog_version"),
    }
    return normalized


def _normalize_search_documents_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    structured_output = payload.get("structured_output")
    if not isinstance(structured_output, dict):
        return normalized
    documents = structured_output.get("documents")
    normalized["structured_output"] = {
        "documents": [
            {
                key: item.get(key)
                for key in (
                    "path",
                    "document_ref",
                    "title",
                    "source",
                    "document_kind",
                    "schema_id",
                    "content_state",
                    "writable",
                    "version",
                    "matched_fields",
                    "match_score",
                )
                if item.get(key) is not None
            }
            for item in documents
            if isinstance(item, dict)
        ],
        "catalog_version": structured_output.get("catalog_version"),
    }
    return normalized


def _drop_redundant_content_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated = deepcopy(items)
    changed = False
    for item in updated:
        if item.get("item_type") != "tool_result":
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        structured_output = payload.get("structured_output")
        content_items = payload.get("content_items")
        if structured_output is None or not isinstance(content_items, list) or not content_items:
            continue
        payload["content_items"] = []
        changed = True
    return updated if changed else items


def _find_largest_text_slot(
    items: list[dict[str, Any]],
    *,
    token_counter: TokenCounter,
) -> tuple[Any, ...] | None:
    best_path: tuple[Any, ...] | None = None
    best_tokens = 0
    for path, value in _iter_text_slots(items):
        text = value.strip()
        if not text:
            continue
        size = token_counter.count(text, "default")
        if size <= best_tokens:
            continue
        best_path = path
        best_tokens = size
    return best_path


def _iter_text_slots(value: Any, path: tuple[Any, ...] = ()) -> list[tuple[tuple[Any, ...], str]]:
    slots: list[tuple[tuple[Any, ...], str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, key)
            if isinstance(child, str) and key in TOOL_RESULT_TEXT_KEYS:
                slots.append((child_path, child))
                continue
            slots.extend(_iter_text_slots(child, child_path))
        return slots
    if isinstance(value, list):
        for index, child in enumerate(value):
            slots.extend(_iter_text_slots(child, (*path, index)))
    return slots


def _read_path(value: Any, path: tuple[Any, ...]) -> Any:
    current = value
    for part in path:
        current = current[part]
    return current


def _write_path(value: Any, path: tuple[Any, ...], replacement: str) -> None:
    current = value
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = replacement


def _replace_latest_items(
    provider_continuation_state: dict[str, Any] | None,
    latest_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(provider_continuation_state, dict):
        return provider_continuation_state
    updated = dict(provider_continuation_state)
    updated["latest_items"] = latest_items
    return updated


def _build_continuation_compaction_snapshot(
    *,
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
    budget_limit_tokens: int,
    estimated_tokens_before: int,
    estimated_tokens_after: int,
    token_counter: TokenCounter,
) -> dict[str, Any]:
    compacted_item_count = _count_compacted_items(original_items, compacted_items)
    trimmed_text_slot_count = _count_trimmed_text_slots(
        original_items,
        compacted_items,
        token_counter=token_counter,
    )
    dropped_content_item_count = _count_dropped_content_items(original_items, compacted_items)
    snapshot = AssistantContinuationCompactionSnapshotDTO(
        trigger_reason="max_input_tokens_exceeded",
        phase="tool_loop_continuation",
        level=(
            "hard"
            if dropped_content_item_count > 0 or len(compacted_items) < len(original_items)
            else "soft"
        ),
        budget_limit_tokens=budget_limit_tokens,
        estimated_tokens_before=estimated_tokens_before,
        estimated_tokens_after=estimated_tokens_after,
        compacted_item_count=max(1, compacted_item_count),
        retained_item_count=len(compacted_items),
        compacted_tool_names=_collect_compacted_tool_names(original_items, compacted_items),
        trimmed_text_slot_count=trimmed_text_slot_count,
        dropped_content_item_count=dropped_content_item_count,
    )
    return snapshot.model_dump(mode="json")


def _count_compacted_items(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
) -> int:
    changed = sum(
        1
        for index, item in enumerate(compacted_items)
        if index >= len(original_items) or item != original_items[index]
    )
    return changed + max(0, len(original_items) - len(compacted_items))


def _collect_compacted_tool_names(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
) -> list[str]:
    tool_names: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(compacted_items):
        original = original_items[index] if index < len(original_items) else None
        if not isinstance(original, dict) or item == original:
            continue
        tool_name = _read_compaction_tool_name(item) or _read_compaction_tool_name(original)
        if tool_name is None or tool_name in seen:
            continue
        seen.add(tool_name)
        tool_names.append(tool_name)
    return tool_names


def _read_compaction_tool_name(item: dict[str, Any]) -> str | None:
    payload = item.get("payload")
    if isinstance(payload, dict):
        tool_name = payload.get("tool_name")
        if isinstance(tool_name, str) and tool_name.strip():
            return tool_name
    tool_name = item.get("tool_name")
    return tool_name if isinstance(tool_name, str) and tool_name.strip() else None


def _count_trimmed_text_slots(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
    *,
    token_counter: TokenCounter,
) -> int:
    original_slots = {path: value for path, value in _iter_text_slots(original_items)}
    compacted_slots = {path: value for path, value in _iter_text_slots(compacted_items)}
    return sum(
        1
        for path, value in compacted_slots.items()
        if path in original_slots
        and value != original_slots[path]
        and token_counter.count(value, "default") <= token_counter.count(original_slots[path], "default")
    )


def _count_dropped_content_items(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
) -> int:
    dropped = 0
    for index, item in enumerate(compacted_items):
        if index >= len(original_items):
            continue
        original_payload = original_items[index].get("payload")
        compacted_payload = item.get("payload")
        if not isinstance(original_payload, dict) or not isinstance(compacted_payload, dict):
            continue
        original_content_items = original_payload.get("content_items")
        compacted_content_items = compacted_payload.get("content_items")
        if not isinstance(original_content_items, list) or not isinstance(compacted_content_items, list):
            continue
        dropped += max(0, len(original_content_items) - len(compacted_content_items))
    return dropped


def _build_budget_exhausted_error() -> AssistantRuntimeTerminalError:
    return AssistantRuntimeTerminalError(
        code="budget_exhausted",
        message="本轮上下文预算已耗尽，压缩后仍无法继续执行。",
    )
