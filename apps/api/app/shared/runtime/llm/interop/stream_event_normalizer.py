from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..llm_interop_profiles import resolve_interop_capabilities
from ..llm_protocol import NormalizedLLMResponse
from ..llm_protocol_responses import parse_generation_response, parse_stream_terminal_response


@dataclass(frozen=True)
class ParsedStreamEvent:
    event_name: str | None
    payload: dict[str, Any]
    delta: str
    reasoning_delta: str = ""
    stop_reason: str | None = None
    terminal_response: NormalizedLLMResponse | None = None


def parse_raw_stream_event(
    api_dialect: str,
    *,
    event_name: str | None,
    payload: dict[str, Any],
    interop_profile: str | None = None,
    tool_name_aliases: dict[str, str] | None = None,
) -> ParsedStreamEvent:
    capabilities = resolve_interop_capabilities(api_dialect, interop_profile)
    stop_reason = extract_stream_stop_reason(api_dialect, event_name, payload)
    return ParsedStreamEvent(
        event_name=event_name,
        payload=payload,
        delta=extract_stream_delta(api_dialect, event_name, payload),
        reasoning_delta=extract_stream_reasoning_delta(
            api_dialect,
            payload,
            captures_reasoning_content=capabilities.captures_chat_reasoning_content,
        ),
        stop_reason=stop_reason,
        terminal_response=(
            None
            if extract_stream_truncation_reason(stop_reason) is not None
            else extract_stream_terminal_response(
                api_dialect,
                event_name,
                payload,
                interop_profile=interop_profile,
                tool_name_aliases=tool_name_aliases,
            )
        ),
    )


def extract_stream_delta(
    api_dialect: str,
    event_name: str | None,
    payload: dict[str, Any],
) -> str:
    if api_dialect == "openai_chat_completions":
        return _extract_openai_chat_delta(payload)
    if api_dialect == "openai_responses":
        return _extract_openai_responses_delta(event_name, payload)
    if api_dialect == "anthropic_messages":
        return _extract_anthropic_delta(payload)
    return _extract_gemini_delta(payload)


def extract_stream_reasoning_delta(
    api_dialect: str,
    payload: dict[str, Any],
    *,
    captures_reasoning_content: bool,
) -> str:
    if api_dialect != "openai_chat_completions" or not captures_reasoning_content:
        return ""
    return _extract_openai_chat_reasoning_delta(payload)


def extract_stream_truncation_reason(stop_reason: str | None) -> str | None:
    if stop_reason is None:
        return None
    normalized = stop_reason.strip()
    if not normalized:
        return None
    if normalized.lower() in {"length", "max_tokens", "max_output_tokens"}:
        return normalized
    if normalized.upper() == "MAX_TOKENS":
        return normalized
    return None


def build_truncated_stream_message(stop_reason: str) -> str:
    return (
        "上游在输出尚未完成时提前停止了这次回复，"
        f"当前只收到部分内容（stop_reason={stop_reason}）。"
        "请缩短问题、关闭流式，或切换更稳定的连接后重试。"
    )


def extract_stream_stop_reason(
    api_dialect: str,
    event_name: str | None,
    payload: dict[str, Any],
) -> str | None:
    if api_dialect == "openai_chat_completions":
        return _extract_openai_chat_stop_reason(payload)
    if api_dialect == "openai_responses":
        return _extract_openai_responses_stop_reason(event_name, payload)
    if api_dialect == "anthropic_messages":
        return _extract_anthropic_stop_reason(payload)
    return _extract_gemini_stop_reason(payload)


def extract_stream_terminal_response(
    api_dialect: str,
    event_name: str | None,
    payload: dict[str, Any],
    *,
    interop_profile: str | None = None,
    tool_name_aliases: dict[str, str] | None = None,
) -> NormalizedLLMResponse | None:
    terminal_payload = _extract_terminal_payload(api_dialect, event_name, payload)
    if terminal_payload is None:
        return None
    return parse_stream_terminal_response(
        api_dialect,
        terminal_payload,
        interop_profile=interop_profile,
        tool_name_aliases=tool_name_aliases,
    )


def synthesize_stream_terminal_response(
    api_dialect: str,
    *,
    raw_events: list[tuple[str | None, dict[str, Any]]],
    tool_name_aliases: dict[str, str] | None = None,
) -> NormalizedLLMResponse | None:
    if api_dialect == "openai_responses":
        return _synthesize_openai_responses_terminal_response(
            raw_events,
            tool_name_aliases=tool_name_aliases or {},
        )
    if api_dialect == "openai_chat_completions":
        return _synthesize_openai_chat_terminal_response(
            raw_events,
            tool_name_aliases=tool_name_aliases or {},
        )
    return None


def _extract_terminal_payload(
    api_dialect: str,
    event_name: str | None,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    if api_dialect == "openai_responses":
        return _extract_openai_responses_terminal_payload(event_name, payload)
    if api_dialect == "gemini_generate_content":
        return _extract_gemini_terminal_payload(payload)
    return None


def _extract_openai_chat_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def _extract_openai_chat_stop_reason(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    finish_reason = first_choice.get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def _extract_openai_chat_reasoning_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
    if not isinstance(delta, dict):
        return ""
    reasoning_content = delta.get("reasoning_content")
    if isinstance(reasoning_content, str):
        return reasoning_content
    if not isinstance(reasoning_content, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in reasoning_content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def _extract_openai_responses_delta(
    event_name: str | None,
    payload: dict[str, Any],
) -> str:
    if event_name == "response.output_text.delta" and isinstance(payload.get("delta"), str):
        return payload["delta"]
    return ""


def _extract_openai_responses_stop_reason(
    event_name: str | None,
    payload: dict[str, Any],
) -> str | None:
    if event_name != "response.completed":
        return None
    incomplete_details = payload.get("incomplete_details")
    if isinstance(incomplete_details, dict):
        reason = incomplete_details.get("reason")
        if isinstance(reason, str):
            return reason
    response = payload.get("response")
    if not isinstance(response, dict):
        return None
    incomplete_details = response.get("incomplete_details")
    if isinstance(incomplete_details, dict):
        reason = incomplete_details.get("reason")
        if isinstance(reason, str):
            return reason
    return None


def _extract_openai_responses_terminal_payload(
    event_name: str | None,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    if event_name != "response.completed":
        return None
    response = payload.get("response")
    if isinstance(response, dict):
        return response
    if isinstance(payload.get("output"), list):
        return payload
    if isinstance(payload.get("output_text"), str):
        return payload
    return None


def _extract_anthropic_delta(payload: dict[str, Any]) -> str:
    delta = payload.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("text"), str):
        return delta["text"]
    return ""


def _extract_anthropic_stop_reason(payload: dict[str, Any]) -> str | None:
    delta = payload.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("stop_reason"), str):
        return delta["stop_reason"]
    stop_reason = payload.get("stop_reason")
    return stop_reason if isinstance(stop_reason, str) else None


def _extract_gemini_delta(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        return ""
    content = candidate.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    return "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def _synthesize_openai_responses_terminal_response(
    raw_events: list[tuple[str | None, dict[str, Any]]],
    *,
    tool_name_aliases: dict[str, str],
) -> NormalizedLLMResponse | None:
    function_calls: dict[str, dict[str, Any]] = {}
    function_call_key_aliases: dict[str, str] = {}
    function_call_orders: dict[str, int] = {}
    output_indexes: dict[str, int] = {}
    completed_response: dict[str, Any] | None = None
    for event_name, payload in raw_events:
        if event_name == "response.completed":
            response = payload.get("response")
            if isinstance(response, dict):
                completed_response = response
            continue
        if event_name in {"response.output_item.added", "response.output_item.done"}:
            item = payload.get("item")
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            item_id, current = _resolve_openai_responses_function_call_entry(
                function_calls=function_calls,
                function_call_key_aliases=function_call_key_aliases,
                function_call_orders=function_call_orders,
                item_id=item.get("id"),
                call_id=item.get("call_id"),
                payload_item_id=payload.get("item_id"),
                fallback_index=len(function_calls),
            )
            _merge_openai_responses_function_call_item(current, item)
            _capture_openai_responses_output_index(
                output_indexes,
                item_id=item_id,
                output_index=payload.get("output_index"),
            )
            continue
        if event_name == "response.function_call_arguments.delta":
            item_id, current = _resolve_openai_responses_function_call_entry(
                function_calls=function_calls,
                function_call_key_aliases=function_call_key_aliases,
                function_call_orders=function_call_orders,
                item_id=payload.get("item_id"),
                call_id=payload.get("call_id"),
                payload_item_id=None,
                fallback_index=len(function_calls),
            )
            delta = payload.get("delta")
            if isinstance(delta, str):
                current["arguments"] = f"{_read_openai_responses_function_call_arguments(current)}{delta}"
            _capture_openai_responses_output_index(
                output_indexes,
                item_id=item_id,
                output_index=payload.get("output_index"),
            )
            continue
        if event_name == "response.function_call_arguments.done":
            item_id, current = _resolve_openai_responses_function_call_entry(
                function_calls=function_calls,
                function_call_key_aliases=function_call_key_aliases,
                function_call_orders=function_call_orders,
                item_id=payload.get("item_id"),
                call_id=payload.get("call_id"),
                payload_item_id=None,
                fallback_index=len(function_calls),
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
                output_indexes,
                item_id=item_id,
                output_index=payload.get("output_index"),
            )
    if not function_calls:
        return None
    reconstructed_payload = dict(completed_response or {})
    reconstructed_payload["output"] = _merge_openai_responses_synthesized_output(
        existing_output=reconstructed_payload.get("output"),
        synthesized_calls=function_calls,
        function_call_key_aliases=function_call_key_aliases,
        function_call_orders=function_call_orders,
        output_indexes=output_indexes,
    )
    return parse_generation_response(
        "openai_responses",
        reconstructed_payload,
        tool_name_aliases=tool_name_aliases,
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


def _synthesize_openai_chat_terminal_response(
    raw_events: list[tuple[str | None, dict[str, Any]]],
    *,
    tool_name_aliases: dict[str, str],
) -> NormalizedLLMResponse | None:
    tool_calls_by_index: dict[int, dict[str, Any]] = {}
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    response_id: str | None = None
    for _, payload in raw_events:
        if response_id is None:
            response_id = _optional_string(payload.get("id"))
        payload_usage = payload.get("usage")
        if isinstance(payload_usage, dict):
            usage = payload_usage
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            continue
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            continue
        choice_finish_reason = _optional_string(first_choice.get("finish_reason"))
        if choice_finish_reason is not None:
            finish_reason = choice_finish_reason
        delta = first_choice.get("delta")
        if not isinstance(delta, dict):
            continue
        tool_calls = delta.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for fallback_index, item in enumerate(tool_calls):
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if not isinstance(index, int):
                index = fallback_index
            current = tool_calls_by_index.setdefault(
                index,
                {
                    "id": None,
                    "type": "function",
                    "function": {
                        "name": "",
                        "arguments": "",
                    },
                },
            )
            call_id = _optional_string(item.get("id"))
            if call_id is not None:
                current["id"] = call_id
            call_type = _optional_string(item.get("type"))
            if call_type is not None:
                current["type"] = call_type
            function = item.get("function")
            if not isinstance(function, dict):
                continue
            name = _optional_string(function.get("name"))
            if name is not None:
                previous_name = current["function"]["name"]
                current["function"]["name"] = (
                    f"{previous_name}{name}" if previous_name and not previous_name.endswith(name) else name
                )
            arguments_chunk = function.get("arguments")
            if isinstance(arguments_chunk, str):
                current["function"]["arguments"] += arguments_chunk
    if not tool_calls_by_index:
        return None
    reconstructed_payload: dict[str, Any] = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [tool_calls_by_index[index] for index in sorted(tool_calls_by_index)],
                },
                "finish_reason": finish_reason or "tool_calls",
            }
        ]
    }
    if usage is not None:
        reconstructed_payload["usage"] = usage
    if response_id is not None:
        reconstructed_payload["id"] = response_id
    return parse_generation_response(
        "openai_chat_completions",
        reconstructed_payload,
        tool_name_aliases=tool_name_aliases,
    )


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _extract_gemini_stop_reason(payload: dict[str, Any]) -> str | None:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        return None
    finish_reason = candidate.get("finishReason")
    return finish_reason if isinstance(finish_reason, str) else None


def _extract_gemini_terminal_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        return None
    content = candidate.get("content")
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        return None
    return payload
