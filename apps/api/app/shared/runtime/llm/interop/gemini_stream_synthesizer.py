from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..llm_protocol_types import NormalizedLLMResponse
from ..llm_protocol_responses import parse_generation_response


@dataclass
class GeminiSynthesisState:
    latest_payload: dict[str, Any] | None = None
    function_call_parts: list[dict[str, Any]] | None = None


def synthesize_gemini_terminal_response(
    raw_events: list[tuple[str | None, dict[str, Any]]],
    *,
    tool_name_aliases: dict[str, str],
) -> NormalizedLLMResponse | None:
    state = GeminiSynthesisState(function_call_parts=[])
    for _, payload in raw_events:
        _apply_gemini_event(state, payload)
    if not state.function_call_parts:
        return None
    reconstructed_payload = dict(state.latest_payload or {})
    candidates = reconstructed_payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        candidates = [{}]
        reconstructed_payload["candidates"] = candidates
    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        first_candidate = {}
        candidates[0] = first_candidate
    content = first_candidate.get("content")
    if not isinstance(content, dict):
        content = {}
        first_candidate["content"] = content
    merged_parts = _merge_gemini_parts(
        content.get("parts"),
        synthesized_parts=state.function_call_parts,
    )
    if not merged_parts:
        return None
    content["parts"] = merged_parts
    return parse_generation_response(
        "gemini_generate_content",
        reconstructed_payload,
        tool_name_aliases=tool_name_aliases,
    )


def _apply_gemini_event(
    state: GeminiSynthesisState,
    payload: dict[str, Any],
) -> None:
    state.latest_payload = payload
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return
    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        return
    content = first_candidate.get("content")
    if not isinstance(content, dict):
        return
    parts = content.get("parts")
    if not isinstance(parts, list):
        return
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("functionCall"), dict):
            continue
        _append_unique_gemini_function_call_part(state.function_call_parts, part)


def _append_unique_gemini_function_call_part(
    function_call_parts: list[dict[str, Any]] | None,
    part: dict[str, Any],
) -> None:
    if function_call_parts is None:
        return
    function_call = part.get("functionCall")
    if not isinstance(function_call, dict):
        return
    call_id = function_call.get("id")
    for existing in function_call_parts:
        existing_call = existing.get("functionCall")
        if not isinstance(existing_call, dict):
            continue
        if call_id and existing_call.get("id") == call_id:
            return
        if existing_call.get("name") == function_call.get("name") and existing_call.get("args") == function_call.get("args"):
            return
    function_call_parts.append(dict(part))


def _merge_gemini_parts(
    existing_parts: Any,
    *,
    synthesized_parts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    if isinstance(existing_parts, list):
        merged.extend(part for part in existing_parts if isinstance(part, dict))
    if not synthesized_parts:
        return merged
    existing_call_ids = {
        part.get("functionCall", {}).get("id")
        for part in merged
        if isinstance(part.get("functionCall"), dict)
    }
    existing_call_signatures = {
        _read_gemini_function_call_signature(part)
        for part in merged
        if _read_gemini_function_call_signature(part) is not None
    }
    for part in synthesized_parts:
        function_call = part.get("functionCall")
        if not isinstance(function_call, dict):
            continue
        call_id = function_call.get("id")
        if call_id and call_id in existing_call_ids:
            continue
        signature = _read_gemini_function_call_signature(part)
        if signature is not None and signature in existing_call_signatures:
            continue
        merged.append(part)
    return merged


def _read_gemini_function_call_signature(part: dict[str, Any]) -> tuple[str | None, str] | None:
    function_call = part.get("functionCall")
    if not isinstance(function_call, dict):
        return None
    name = function_call.get("name")
    args = function_call.get("args")
    serialized_args = repr(args)
    return (name if isinstance(name, str) else None, serialized_args)
