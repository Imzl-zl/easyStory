from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .codec_value_helpers import optional_string as _optional_string
from ..llm_protocol_types import NormalizedLLMResponse
from ..llm_protocol_responses import parse_generation_response


@dataclass
class OpenAIResponsesSynthesisState:
    function_calls: dict[str, dict[str, Any]]
    function_call_key_aliases: dict[str, str]
    function_call_orders: dict[str, int]
    output_indexes: dict[str, int]
    completed_response: dict[str, Any] | None = None


def synthesize_openai_responses_terminal_response(
    raw_events: list[tuple[str | None, dict[str, Any]]],
    *,
    tool_name_aliases: dict[str, str],
) -> NormalizedLLMResponse | None:
    state = OpenAIResponsesSynthesisState(
        function_calls={},
        function_call_key_aliases={},
        function_call_orders={},
        output_indexes={},
    )
    for event_name, payload in raw_events:
        _apply_openai_responses_event(state, event_name, payload)
    if not state.function_calls:
        return None
    reconstructed_payload = dict(state.completed_response or {})
    reconstructed_payload["output"] = _merge_openai_responses_synthesized_output(
        existing_output=reconstructed_payload.get("output"),
        synthesized_calls=state.function_calls,
        function_call_key_aliases=state.function_call_key_aliases,
        function_call_orders=state.function_call_orders,
        output_indexes=state.output_indexes,
    )
    return parse_generation_response(
        "openai_responses",
        reconstructed_payload,
        tool_name_aliases=tool_name_aliases,
    )


def _apply_openai_responses_event(
    state: OpenAIResponsesSynthesisState,
    event_name: str | None,
    payload: dict[str, Any],
) -> None:
    if event_name == "response.completed":
        response = payload.get("response")
        if isinstance(response, dict):
            state.completed_response = response
        return
    if event_name in {"response.output_item.added", "response.output_item.done"}:
        _apply_openai_responses_output_item_event(state, payload)
        return
    if event_name == "response.function_call_arguments.delta":
        _apply_openai_responses_arguments_delta_event(state, payload)
        return
    if event_name == "response.function_call_arguments.done":
        _apply_openai_responses_arguments_done_event(state, payload)


def _apply_openai_responses_output_item_event(
    state: OpenAIResponsesSynthesisState,
    payload: dict[str, Any],
) -> None:
    item = payload.get("item")
    if not isinstance(item, dict) or item.get("type") != "function_call":
        return
    item_id, current = _resolve_openai_responses_function_call_entry(
        function_calls=state.function_calls,
        function_call_key_aliases=state.function_call_key_aliases,
        function_call_orders=state.function_call_orders,
        item_id=item.get("id"),
        call_id=item.get("call_id"),
        payload_item_id=payload.get("item_id"),
        fallback_index=len(state.function_calls),
    )
    _merge_openai_responses_function_call_item(current, item)
    _capture_openai_responses_output_index(
        state.output_indexes,
        item_id=item_id,
        output_index=payload.get("output_index"),
    )


def _apply_openai_responses_arguments_delta_event(
    state: OpenAIResponsesSynthesisState,
    payload: dict[str, Any],
) -> None:
    item_id, current = _resolve_openai_responses_function_call_entry(
        function_calls=state.function_calls,
        function_call_key_aliases=state.function_call_key_aliases,
        function_call_orders=state.function_call_orders,
        item_id=payload.get("item_id"),
        call_id=payload.get("call_id"),
        payload_item_id=None,
        fallback_index=len(state.function_calls),
    )
    delta = payload.get("delta")
    if isinstance(delta, str):
        current["arguments"] = f"{_read_openai_responses_function_call_arguments(current)}{delta}"
    _capture_openai_responses_output_index(
        state.output_indexes,
        item_id=item_id,
        output_index=payload.get("output_index"),
    )


def _apply_openai_responses_arguments_done_event(
    state: OpenAIResponsesSynthesisState,
    payload: dict[str, Any],
) -> None:
    item_id, current = _resolve_openai_responses_function_call_entry(
        function_calls=state.function_calls,
        function_call_key_aliases=state.function_call_key_aliases,
        function_call_orders=state.function_call_orders,
        item_id=payload.get("item_id"),
        call_id=payload.get("call_id"),
        payload_item_id=None,
        fallback_index=len(state.function_calls),
    )
    call_id = _optional_string(payload.get("call_id"))
    if call_id is not None:
        current["call_id"] = call_id
    name = _optional_string(payload.get("name"))
    if name is not None:
        current["name"] = name
    arguments = payload.get("arguments")
    if isinstance(arguments, str):
        current["arguments"] = arguments
    _capture_openai_responses_output_index(
        state.output_indexes,
        item_id=item_id,
        output_index=payload.get("output_index"),
    )


def _resolve_openai_responses_function_call_entry(
    *,
    function_calls: dict[str, dict[str, Any]],
    function_call_key_aliases: dict[str, str],
    function_call_orders: dict[str, int],
    item_id: Any,
    call_id: Any,
    payload_item_id: Any,
    fallback_index: int,
) -> tuple[str, dict[str, Any]]:
    resolved_call_id = _optional_string(call_id)
    resolved_item_id = _optional_string(item_id)
    resolved_payload_item_id = _optional_string(payload_item_id)
    resolved_key = _lookup_openai_responses_function_call_alias(
        function_call_key_aliases,
        resolved_call_id,
        resolved_item_id,
        resolved_payload_item_id,
    )
    if resolved_key is None:
        resolved_key = (
            resolved_call_id
            or resolved_item_id
            or resolved_payload_item_id
            or f"function_call:{fallback_index}"
        )
    current = function_calls.setdefault(
        resolved_key,
        {"type": "function_call"},
    )
    if resolved_key not in function_call_orders:
        function_call_orders[resolved_key] = len(function_call_orders)
    if resolved_call_id is not None:
        current["call_id"] = resolved_call_id
        function_call_key_aliases[resolved_call_id] = resolved_key
    preferred_item_id = resolved_item_id or resolved_payload_item_id
    if preferred_item_id is not None:
        current["id"] = preferred_item_id
        function_call_key_aliases[preferred_item_id] = resolved_key
    return resolved_key, current


def _lookup_openai_responses_function_call_alias(
    function_call_key_aliases: dict[str, str],
    *candidates: str | None,
) -> str | None:
    for candidate in candidates:
        if candidate is None:
            continue
        resolved = function_call_key_aliases.get(candidate)
        if resolved is not None:
            return resolved
    return None


def _merge_openai_responses_function_call_item(
    current: dict[str, Any],
    item: dict[str, Any],
) -> None:
    item_id = _optional_string(item.get("id"))
    if item_id is not None:
        current["id"] = item_id
    call_id = _optional_string(item.get("call_id"))
    if call_id is not None:
        current["call_id"] = call_id
    name = _optional_string(item.get("name"))
    if name is not None:
        current["name"] = name
    arguments = item.get("arguments")
    if isinstance(arguments, str):
        current["arguments"] = arguments


def _read_openai_responses_function_call_arguments(current: dict[str, Any]) -> str:
    arguments = current.get("arguments")
    if isinstance(arguments, str):
        return arguments
    return ""


def _capture_openai_responses_output_index(
    output_indexes: dict[str, int],
    *,
    item_id: str,
    output_index: Any,
) -> None:
    if isinstance(output_index, int):
        output_indexes[item_id] = output_index


def _merge_openai_responses_synthesized_output(
    *,
    existing_output: Any,
    synthesized_calls: dict[str, dict[str, Any]],
    function_call_key_aliases: dict[str, str],
    function_call_orders: dict[str, int],
    output_indexes: dict[str, int],
) -> list[dict[str, Any]]:
    ordered_calls = [
        synthesized_calls[item_id]
        for item_id in sorted(
            synthesized_calls,
            key=lambda candidate: (
                output_indexes.get(candidate, 1_000_000),
                function_call_orders.get(candidate, 1_000_000),
                candidate,
            ),
        )
    ]
    if not isinstance(existing_output, list) or not existing_output:
        return ordered_calls
    remaining_calls = dict(synthesized_calls)
    surviving_output_items: list[dict[str, Any]] = []
    for item in existing_output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "function_call":
            surviving_output_items.append(item)
            continue
        key = _lookup_openai_responses_function_call_key(
            remaining_calls,
            function_call_key_aliases=function_call_key_aliases,
            item_id=item.get("id"),
            call_id=item.get("call_id"),
            payload_item_id=None,
        )
        replacement = remaining_calls.pop(key, None) if key is not None else None
        surviving_output_items.append(replacement or item)
    pending_insertions = _group_openai_responses_function_call_insertions(
        existing_output=existing_output,
        remaining_calls=remaining_calls,
        function_call_key_aliases=function_call_key_aliases,
        function_call_orders=function_call_orders,
        output_indexes=output_indexes,
    )
    return _rebuild_openai_responses_output_transcript(
        surviving_output_items=surviving_output_items,
        pending_insertions=pending_insertions,
    )


def _lookup_openai_responses_function_call_key(
    synthesized_calls: dict[str, dict[str, Any]],
    *,
    function_call_key_aliases: dict[str, str],
    item_id: Any,
    call_id: Any,
    payload_item_id: Any,
) -> str | None:
    resolved_call_id = _optional_string(call_id)
    resolved_item_id = _optional_string(item_id)
    resolved_payload_item_id = _optional_string(payload_item_id)
    for candidate in (
        resolved_call_id,
        resolved_item_id,
        resolved_payload_item_id,
    ):
        if candidate is None:
            continue
        resolved_key = function_call_key_aliases.get(candidate, candidate)
        if resolved_key in synthesized_calls:
            return resolved_key
    return None


def _group_openai_responses_function_call_insertions(
    *,
    existing_output: list[Any],
    remaining_calls: dict[str, dict[str, Any]],
    function_call_key_aliases: dict[str, str],
    function_call_orders: dict[str, int],
    output_indexes: dict[str, int],
) -> dict[int, list[dict[str, Any]]]:
    existing_function_call_keys = {
        key
        for item in existing_output
        if isinstance(item, dict) and item.get("type") == "function_call"
        for key in [
            _lookup_openai_responses_function_call_key(
                remaining_calls,
                function_call_key_aliases=function_call_key_aliases,
                item_id=item.get("id"),
                call_id=item.get("call_id"),
                payload_item_id=None,
            )
        ]
        if key is not None
    }
    insertions: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for item_id, call in remaining_calls.items():
        if item_id in existing_function_call_keys:
            continue
        target_index = output_indexes.get(item_id, len(existing_output))
        insertions.setdefault(target_index, []).append(
            (function_call_orders.get(item_id, len(function_call_orders)), call)
        )
    return {
        index: [
            item
            for _, item in sorted(group, key=lambda candidate: candidate[0])
        ]
        for index, group in insertions.items()
    }


def _rebuild_openai_responses_output_transcript(
    *,
    surviving_output_items: list[dict[str, Any]],
    pending_insertions: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    if not pending_insertions:
        return list(surviving_output_items)
    rebuilt_output: list[dict[str, Any]] = []
    existing_index = 0
    slot_index = 0
    max_insertion_index = max(pending_insertions)
    while existing_index < len(surviving_output_items) or slot_index <= max_insertion_index:
        insertion_group = pending_insertions.get(slot_index)
        if insertion_group:
            rebuilt_output.extend(insertion_group)
            slot_index += 1
            continue
        if existing_index < len(surviving_output_items):
            rebuilt_output.append(surviving_output_items[existing_index])
            existing_index += 1
        slot_index += 1
    return rebuilt_output
