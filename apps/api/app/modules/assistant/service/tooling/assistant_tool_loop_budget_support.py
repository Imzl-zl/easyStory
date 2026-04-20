from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.shared.runtime.llm.llm_protocol_types import LLMContinuationSupport
from app.shared.runtime.token_counter import TokenCounter

from ..context.assistant_input_budget_support import (
    estimate_assistant_request_tokens,
    trim_text_to_token_budget,
)
from ..assistant_compaction_contract_support import (
    build_compaction_budget_exhausted_error,
    resolve_continuation_compaction_level,
)
from ..assistant_run_budget import AssistantRunBudget
from ..dto import (
    AssistantContinuationCompactionSnapshotDTO,
    build_structured_items_digest,
)

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
        raise build_compaction_budget_exhausted_error()
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
        raise build_compaction_budget_exhausted_error()
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
            reduced = _reduce_compacted_items(compacted)
            if reduced == compacted:
                return compacted
            compacted = reduced
            continue
        current_text = _read_path(compacted, slot_path)
        if not isinstance(current_text, str) or not current_text.strip():
            reduced = _reduce_compacted_items(compacted)
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
            reduced = _reduce_compacted_items(compacted)
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


def _drop_redundant_resource_links(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated = deepcopy(items)
    changed = False
    for item in updated:
        if item.get("item_type") != "tool_result":
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        structured_output = payload.get("structured_output")
        resource_links = payload.get("resource_links")
        if structured_output is None or not isinstance(resource_links, list) or not resource_links:
            continue
        payload["resource_links"] = []
        changed = True
    return updated if changed else items


def _reduce_compacted_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reduced = _drop_redundant_content_items(items)
    if reduced != items:
        return reduced
    reduced = _drop_redundant_resource_links(items)
    if reduced != items:
        return reduced
    return _drop_oldest_continuation_block(items)


def _drop_oldest_continuation_block(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(items) <= 1:
        return items
    block_end = _resolve_continuation_block_end(items, 0)
    if block_end >= len(items):
        return items
    return list(items[block_end:])


def _resolve_continuation_block_end(items: list[dict[str, Any]], start_index: int) -> int:
    if start_index >= len(items):
        return start_index
    item = items[start_index]
    if not isinstance(item, dict):
        return start_index + 1
    cycle_index = _read_continuation_cycle_index(item)
    if cycle_index is not None:
        return _consume_same_cycle(items, start_index, cycle_index)
    if item.get("item_type") != "message":
        return start_index + 1
    next_index = start_index + 1
    if next_index >= len(items):
        return next_index
    next_item = items[next_index]
    if not isinstance(next_item, dict):
        return next_index
    next_cycle_index = _read_continuation_cycle_index(next_item)
    if next_cycle_index is None:
        return next_index
    return _consume_same_cycle(items, next_index, next_cycle_index)


def _consume_same_cycle(items: list[dict[str, Any]], start_index: int, cycle_index: int) -> int:
    index = start_index
    while index < len(items):
        item = items[index]
        if not isinstance(item, dict):
            break
        if item.get("item_type") not in {"tool_call", "tool_result"}:
            break
        if _read_continuation_cycle_index(item) != cycle_index:
            break
        index += 1
    return index


def _read_continuation_cycle_index(item: dict[str, Any]) -> int | None:
    value = item.get("tool_cycle_index")
    if isinstance(value, int) and value >= 0:
        return value
    return None


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
    prefix_drop_count = _resolve_prefix_drop_count(original_items, compacted_items)
    compacted_source_items = _collect_compacted_source_items(
        original_items,
        compacted_items,
        prefix_drop_count=prefix_drop_count,
    )
    compacted_item_count = len(compacted_source_items)
    trimmed_text_slot_count = _count_trimmed_text_slots(
        original_items,
        compacted_items,
        token_counter=token_counter,
        prefix_drop_count=prefix_drop_count,
    )
    dropped_content_item_count = _count_dropped_content_items(
        original_items,
        compacted_items,
        prefix_drop_count=prefix_drop_count,
    )
    snapshot = AssistantContinuationCompactionSnapshotDTO(
        trigger_reason="max_input_tokens_exceeded",
        phase="tool_loop_continuation",
        level=resolve_continuation_compaction_level(
            original_item_count=len(original_items),
            retained_item_count=len(compacted_items),
            dropped_content_item_count=dropped_content_item_count,
        ),
        budget_limit_tokens=budget_limit_tokens,
        estimated_tokens_before=estimated_tokens_before,
        estimated_tokens_after=estimated_tokens_after,
        compacted_item_count=max(1, compacted_item_count),
        retained_item_count=len(compacted_items),
        compressed_items_digest=(
            build_structured_items_digest(compacted_source_items)
            if compacted_source_items
            else None
        ),
        projected_items_digest=build_structured_items_digest(compacted_items),
        compacted_tool_names=_collect_compacted_tool_names(compacted_source_items),
        compacted_document_refs=_collect_compacted_document_refs(compacted_source_items),
        compacted_document_versions=_collect_compacted_document_versions(compacted_source_items),
        compacted_catalog_versions=_collect_compacted_catalog_versions(compacted_source_items),
        trimmed_text_slot_count=trimmed_text_slot_count,
        dropped_content_item_count=dropped_content_item_count,
    )
    return snapshot.model_dump(mode="json")


def _resolve_prefix_drop_count(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
) -> int:
    # Current hard compaction only deletes the oldest prefix block and never reorders items.
    return max(0, len(original_items) - len(compacted_items))


def _collect_compacted_source_items(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
    *,
    prefix_drop_count: int,
) -> list[dict[str, Any]]:
    source_items = list(original_items[:prefix_drop_count])
    for original, compacted in _iter_retained_compaction_pairs(
        original_items,
        compacted_items,
        prefix_drop_count=prefix_drop_count,
    ):
        if original != compacted:
            source_items.append(original)
    return source_items


def _collect_compacted_tool_names(
    compacted_source_items: list[dict[str, Any]],
) -> list[str]:
    tool_names: list[str] = []
    seen: set[str] = set()
    for item in compacted_source_items:
        tool_name = _read_compaction_tool_name(item)
        if tool_name is None or tool_name in seen:
            continue
        seen.add(tool_name)
        tool_names.append(tool_name)
    return tool_names


def _collect_compacted_document_refs(
    compacted_source_items: list[dict[str, Any]],
) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for item in compacted_source_items:
        for document_ref in _iter_compaction_document_refs(item):
            if document_ref in seen:
                continue
            seen.add(document_ref)
            refs.append(document_ref)
    return refs


def _collect_compacted_document_versions(
    compacted_source_items: list[dict[str, Any]],
) -> dict[str, str]:
    versions: dict[str, str] = {}
    for item in compacted_source_items:
        _merge_compaction_document_versions(versions, item)
    return dict(sorted(versions.items()))


def _collect_compacted_catalog_versions(
    compacted_source_items: list[dict[str, Any]],
) -> list[str]:
    versions: list[str] = []
    seen: set[str] = set()
    for item in compacted_source_items:
        catalog_version = _read_compaction_catalog_version(item)
        if catalog_version is None or catalog_version in seen:
            continue
        seen.add(catalog_version)
        versions.append(catalog_version)
    return versions


def _iter_retained_compaction_pairs(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
    *,
    prefix_drop_count: int,
) -> tuple[tuple[dict[str, Any], dict[str, Any]], ...]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for index, compacted in enumerate(compacted_items):
        original_index = prefix_drop_count + index
        if original_index >= len(original_items):
            break
        original = original_items[original_index]
        if not isinstance(original, dict) or not isinstance(compacted, dict):
            continue
        pairs.append((original, compacted))
    return tuple(pairs)


def _read_compaction_tool_name(item: dict[str, Any]) -> str | None:
    payload = item.get("payload")
    if isinstance(payload, dict):
        tool_name = payload.get("tool_name")
        if isinstance(tool_name, str) and tool_name.strip():
            return tool_name
    tool_name = item.get("tool_name")
    return tool_name if isinstance(tool_name, str) and tool_name.strip() else None


def _iter_compaction_document_refs(item: dict[str, Any]) -> tuple[str, ...]:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return ()
    structured_output = payload.get("structured_output")
    if not isinstance(structured_output, dict):
        return ()
    documents = structured_output.get("documents")
    if not isinstance(documents, list):
        return ()
    refs: list[str] = []
    seen: set[str] = set()
    for document in documents:
        if not isinstance(document, dict):
            continue
        document_ref = document.get("document_ref")
        if not isinstance(document_ref, str):
            continue
        normalized = document_ref.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        refs.append(normalized)
    return tuple(refs)


def _merge_compaction_document_versions(
    versions: dict[str, str],
    item: dict[str, Any],
) -> None:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return
    structured_output = payload.get("structured_output")
    if not isinstance(structured_output, dict):
        return
    documents = structured_output.get("documents")
    if not isinstance(documents, list):
        return
    for document in documents:
        if not isinstance(document, dict):
            continue
        document_ref = document.get("document_ref")
        version = document.get("version")
        if not isinstance(document_ref, str) or not isinstance(version, str):
            continue
        normalized_ref = document_ref.strip()
        normalized_version = version.strip()
        if not normalized_ref or not normalized_version:
            continue
        versions.setdefault(normalized_ref, normalized_version)


def _read_compaction_catalog_version(item: dict[str, Any]) -> str | None:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    structured_output = payload.get("structured_output")
    if not isinstance(structured_output, dict):
        return None
    catalog_version = structured_output.get("catalog_version")
    if not isinstance(catalog_version, str):
        return None
    normalized = catalog_version.strip()
    if not normalized:
        return None
    return normalized


def _count_trimmed_text_slots(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
    *,
    token_counter: TokenCounter,
    prefix_drop_count: int,
) -> int:
    trimmed = 0
    for original, compacted in _iter_retained_compaction_pairs(
        original_items,
        compacted_items,
        prefix_drop_count=prefix_drop_count,
    ):
        original_slots = {path: value for path, value in _iter_text_slots(original)}
        compacted_slots = {path: value for path, value in _iter_text_slots(compacted)}
        trimmed += sum(
            1
            for path, value in compacted_slots.items()
            if path in original_slots
            and value != original_slots[path]
            and token_counter.count(value, "default")
            <= token_counter.count(original_slots[path], "default")
        )
    return trimmed


def _count_dropped_content_items(
    original_items: list[dict[str, Any]],
    compacted_items: list[dict[str, Any]],
    *,
    prefix_drop_count: int,
) -> int:
    dropped = 0
    for original, compacted in _iter_retained_compaction_pairs(
        original_items,
        compacted_items,
        prefix_drop_count=prefix_drop_count,
    ):
        original_payload = original.get("payload")
        compacted_payload = compacted.get("payload")
        if not isinstance(original_payload, dict) or not isinstance(compacted_payload, dict):
            continue
        original_content_items = original_payload.get("content_items")
        compacted_content_items = compacted_payload.get("content_items")
        if not isinstance(original_content_items, list) or not isinstance(compacted_content_items, list):
            continue
        dropped += max(0, len(original_content_items) - len(compacted_content_items))
    return dropped
