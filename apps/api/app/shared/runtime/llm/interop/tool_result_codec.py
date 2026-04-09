from __future__ import annotations

import json
from typing import Any, Mapping

from .tool_name_codec import ToolNamePolicy, encode_tool_name

_INTERNAL_TOOL_RESULT_KEYS = frozenset({"audit", "tool_cycle_index", "tool_call_id"})


def build_openai_chat_tool_result_message(
    item: dict[str, Any],
    *,
    tool_name_aliases: Mapping[str, str],
    tool_name_policy: ToolNamePolicy,
) -> dict[str, Any] | None:
    call_id = _read_tool_result_call_id(item)
    payload = _read_tool_result_payload(item)
    if call_id is None or payload is None:
        return None
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": _serialize_tool_result_payload(
            item,
            payload,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        ),
    }


def build_anthropic_tool_result_message(
    item: dict[str, Any],
    *,
    tool_name_aliases: Mapping[str, str],
    tool_name_policy: ToolNamePolicy,
) -> dict[str, Any] | None:
    call_id = _read_tool_result_call_id(item)
    payload = _read_tool_result_payload(item)
    if call_id is None or payload is None:
        return None
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": call_id,
                "is_error": item.get("status") == "errored",
                "content": _serialize_tool_result_payload(
                    item,
                    payload,
                    tool_name_aliases=tool_name_aliases,
                    tool_name_policy=tool_name_policy,
                ),
            }
        ],
    }


def build_gemini_tool_result_content(
    item: dict[str, Any],
    *,
    tool_call_meta_by_call_id: dict[str, dict[str, Any]],
    tool_name_aliases: Mapping[str, str],
    tool_name_policy: ToolNamePolicy,
) -> dict[str, Any] | None:
    payload = _read_tool_result_payload(item)
    call_id = _read_tool_result_call_id(item)
    if payload is None or call_id is None:
        return None
    tool_call_meta = tool_call_meta_by_call_id.get(call_id)
    external_tool_name = _read_gemini_external_tool_name(tool_call_meta)
    if external_tool_name is None:
        external_tool_name = _read_tool_result_tool_name(
            item,
            payload,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
    if external_tool_name is None:
        return None
    function_response: dict[str, Any] = {
        "name": external_tool_name,
        "response": _build_provider_visible_tool_result_payload(item, payload),
    }
    function_call_id = _read_gemini_function_call_id(tool_call_meta)
    if function_call_id is not None:
        function_response["id"] = function_call_id
    return {
        "role": "user",
        "parts": [{"functionResponse": function_response}],
    }


def build_openai_responses_function_call_outputs(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for item in items:
        if item.get("item_type") != "tool_result":
            continue
        payload = _read_tool_result_payload(item)
        call_id = _read_tool_result_call_id(item)
        if payload is None or call_id is None:
            continue
        structured_output = payload.get("structured_output")
        if structured_output is None:
            continue
        outputs.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(
                    structured_output,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            }
        )
    return outputs


def _read_tool_result_call_id(item: dict[str, Any]) -> str | None:
    call_id = item.get("call_id")
    if not isinstance(call_id, str):
        return None
    stripped = call_id.strip()
    return stripped or None


def _read_tool_result_payload(item: dict[str, Any]) -> dict[str, Any] | None:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    return payload


def _serialize_tool_result_payload(
    item: dict[str, Any],
    payload: dict[str, Any],
    *,
    tool_name_aliases: Mapping[str, str],
    tool_name_policy: ToolNamePolicy,
) -> str:
    result_payload = _build_provider_visible_tool_result_payload(item, payload)
    tool_name = _read_tool_result_tool_name(
        item,
        payload,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )
    if tool_name is not None:
        result_payload["tool_name"] = tool_name
    status = item.get("status")
    if isinstance(status, str) and status.strip():
        result_payload["status"] = status.strip()
    return json.dumps(
        result_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _build_provider_visible_tool_result_payload(
    item: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = {
        key: value
        for key, value in payload.items()
        if key not in _INTERNAL_TOOL_RESULT_KEYS
    }
    status = item.get("status")
    if isinstance(status, str) and status.strip():
        response["status"] = status.strip()
    return response


def _read_tool_result_tool_name(
    item: dict[str, Any],
    payload: dict[str, Any],
    *,
    tool_name_aliases: Mapping[str, str],
    tool_name_policy: ToolNamePolicy,
) -> str | None:
    for candidate in (item.get("tool_name"), payload.get("tool_name")):
        if isinstance(candidate, str) and candidate.strip():
            return encode_tool_name(
                candidate,
                tool_name_aliases=tool_name_aliases,
                policy=tool_name_policy,
            )
    return None


def _read_gemini_external_tool_name(tool_call_meta: dict[str, Any] | None) -> str | None:
    if not isinstance(tool_call_meta, dict):
        return None
    value = tool_call_meta.get("external_tool_name")
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _read_gemini_function_call_id(tool_call_meta: dict[str, Any] | None) -> str | None:
    if not isinstance(tool_call_meta, dict):
        return None
    provider_payload = tool_call_meta.get("provider_payload")
    if not isinstance(provider_payload, dict):
        return None
    function_call = provider_payload.get("functionCall")
    if not isinstance(function_call, dict):
        return None
    value = function_call.get("id")
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
