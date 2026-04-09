from __future__ import annotations

from typing import Any

from .tool_name_codec import encode_tool_name
from .tool_result_codec import (
    build_gemini_tool_result_content as codec_build_gemini_tool_result_content,
)


def project_continuation_to_gemini_contents(
    items: list[dict[str, Any]],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    tool_call_meta_by_call_id: dict[str, dict[str, Any]] = {}
    index = 0
    while index < len(items):
        item = items[index]
        if not isinstance(item, dict):
            index += 1
            continue
        item_type = item.get("item_type")
        if item_type == "message":
            gemini_text_content = _build_gemini_text_content(item)
            if gemini_text_content is not None:
                contents.append(gemini_text_content)
            index += 1
            continue
        cycle_index = _read_tool_cycle_index(item)
        if cycle_index is not None and item_type in {"tool_call", "tool_result"}:
            next_index, cycle_contents = _build_gemini_tool_cycle_contents(
                items,
                start_index=index,
                tool_cycle_index=cycle_index,
                tool_call_meta_by_call_id=tool_call_meta_by_call_id,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            contents.extend(cycle_contents)
            index = next_index
            continue
        if item_type == "tool_call":
            next_index, tool_call_content = _build_gemini_tool_call_step_content(
                items,
                start_index=index,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
                tool_call_meta_by_call_id=tool_call_meta_by_call_id,
            )
            if tool_call_content is not None:
                contents.append(tool_call_content)
            index = next_index
            continue
        if item_type == "tool_result":
            next_index, tool_result_content = _build_gemini_tool_result_step_content(
                items,
                start_index=index,
                tool_call_meta_by_call_id=tool_call_meta_by_call_id,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_result_content is not None:
                contents.append(tool_result_content)
            index = next_index
            continue
        index += 1
    return contents


def _build_gemini_tool_cycle_contents(
    items: list[dict[str, Any]],
    *,
    start_index: int,
    tool_cycle_index: int,
    tool_call_meta_by_call_id: dict[str, dict[str, Any]],
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> tuple[int, list[dict[str, Any]]]:
    cycle_items: list[dict[str, Any]] = []
    index = start_index
    while index < len(items):
        item = items[index]
        if not isinstance(item, dict):
            break
        if item.get("item_type") not in {"tool_call", "tool_result"}:
            break
        if _read_tool_cycle_index(item) != tool_cycle_index:
            break
        cycle_items.append(item)
        index += 1
    contents: list[dict[str, Any]] = []
    tool_call_parts = _build_gemini_tool_cycle_call_parts(
        cycle_items,
        tool_call_meta_by_call_id=tool_call_meta_by_call_id,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )
    if tool_call_parts:
        contents.append({"role": "model", "parts": tool_call_parts})
    tool_result_parts = _build_gemini_tool_cycle_result_parts(
        cycle_items,
        tool_call_meta_by_call_id=tool_call_meta_by_call_id,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )
    if tool_result_parts:
        contents.append({"role": "user", "parts": tool_result_parts})
    return index, contents


def _build_gemini_tool_cycle_call_parts(
    items: list[dict[str, Any]],
    *,
    tool_call_meta_by_call_id: dict[str, dict[str, Any]],
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for item in items:
        if item.get("item_type") != "tool_call":
            continue
        tool_call_content, tool_call_meta = _build_gemini_tool_call_content(
            item,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
        tool_call_part = _read_gemini_single_part(tool_call_content, "functionCall")
        if tool_call_part is None or tool_call_meta is None:
            continue
        call_id = item.get("call_id")
        if isinstance(call_id, str) and call_id.strip():
            tool_call_meta_by_call_id[call_id.strip()] = tool_call_meta
        parts.append(tool_call_part)
    return parts


def _build_gemini_tool_cycle_result_parts(
    items: list[dict[str, Any]],
    *,
    tool_call_meta_by_call_id: dict[str, dict[str, Any]],
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for item in items:
        if item.get("item_type") != "tool_result":
            continue
        tool_result_content = codec_build_gemini_tool_result_content(
            item,
            tool_call_meta_by_call_id=tool_call_meta_by_call_id,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
        tool_result_part = _read_gemini_single_part(tool_result_content, "functionResponse")
        if tool_result_part is not None:
            parts.append(tool_result_part)
    return parts


def _build_gemini_tool_call_step_content(
    items: list[dict[str, Any]],
    *,
    start_index: int,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
    tool_call_meta_by_call_id: dict[str, dict[str, Any]],
) -> tuple[int, dict[str, Any] | None]:
    parts: list[dict[str, Any]] = []
    index = start_index
    while index < len(items):
        item = items[index]
        if not isinstance(item, dict) or item.get("item_type") != "tool_call":
            break
        tool_call_content, tool_call_meta = _build_gemini_tool_call_content(
            item,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
        tool_call_part = _read_gemini_single_part(tool_call_content, "functionCall")
        if tool_call_part is not None and tool_call_meta is not None:
            call_id = item.get("call_id")
            if isinstance(call_id, str) and call_id.strip():
                tool_call_meta_by_call_id[call_id.strip()] = tool_call_meta
            parts.append(tool_call_part)
        index += 1
    if not parts:
        return index, None
    return index, {"role": "model", "parts": parts}


def _build_gemini_tool_result_step_content(
    items: list[dict[str, Any]],
    *,
    start_index: int,
    tool_call_meta_by_call_id: dict[str, dict[str, Any]],
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> tuple[int, dict[str, Any] | None]:
    parts: list[dict[str, Any]] = []
    index = start_index
    while index < len(items):
        item = items[index]
        if not isinstance(item, dict) or item.get("item_type") != "tool_result":
            break
        tool_result_content = codec_build_gemini_tool_result_content(
            item,
            tool_call_meta_by_call_id=tool_call_meta_by_call_id,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
        tool_result_part = _read_gemini_single_part(tool_result_content, "functionResponse")
        if tool_result_part is not None:
            parts.append(tool_result_part)
        index += 1
    if not parts:
        return index, None
    return index, {"role": "user", "parts": parts}


def _read_gemini_single_part(
    content: dict[str, Any] | None,
    expected_key: str,
) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list) or len(parts) != 1:
        return None
    part = parts[0]
    if not isinstance(part, dict) or expected_key not in part:
        return None
    return part


def _read_tool_cycle_index(item: dict[str, Any]) -> int | None:
    value = item.get("tool_cycle_index")
    if isinstance(value, int) and value >= 0:
        return value
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    value = payload.get("tool_cycle_index")
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _build_gemini_text_content(item: dict[str, Any]) -> dict[str, Any] | None:
    role = item.get("role")
    content = item.get("content")
    if role not in {"user", "assistant"}:
        return None
    if not isinstance(content, str) or not content.strip():
        return None
    return {
        "role": "model" if role == "assistant" else "user",
        "parts": [{"text": content.strip()}],
    }


def _build_gemini_tool_call_content(
    item: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None, None
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return None, None
    arguments = payload.get("arguments")
    provider_payload = _read_provider_payload(payload)
    preserved_part = _build_preserved_gemini_tool_call_part(
        provider_payload,
        fallback_tool_name=tool_name,
        fallback_arguments=arguments if isinstance(arguments, dict) else {},
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )
    if preserved_part is not None:
        function_call = preserved_part.get("functionCall")
        if isinstance(function_call, dict):
            external_tool_name = function_call.get("name")
            if isinstance(external_tool_name, str) and external_tool_name.strip():
                return (
                    {"role": "model", "parts": [preserved_part]},
                    {
                        "external_tool_name": external_tool_name.strip(),
                        "provider_payload": provider_payload,
                    },
                )
    external_tool_name = encode_tool_name(
        tool_name,
        tool_name_aliases=tool_name_aliases,
        policy=tool_name_policy,
    )
    return (
        {
            "role": "model",
            "parts": [
                {
                    "functionCall": {
                        "name": external_tool_name,
                        "args": arguments if isinstance(arguments, dict) else {},
                    }
                }
            ],
        },
        {
            "external_tool_name": external_tool_name,
            "provider_payload": provider_payload,
        },
    )


def _build_preserved_gemini_tool_call_part(
    provider_payload: dict[str, Any] | None,
    *,
    fallback_tool_name: str,
    fallback_arguments: dict[str, Any],
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> dict[str, Any] | None:
    if not isinstance(provider_payload, dict):
        return None
    function_call = provider_payload.get("functionCall")
    if not isinstance(function_call, dict):
        return None
    preserved_part = dict(provider_payload)
    preserved_function_call = dict(function_call)
    if not isinstance(preserved_function_call.get("name"), str) or not preserved_function_call.get(
        "name", ""
    ).strip():
        preserved_function_call["name"] = encode_tool_name(
            fallback_tool_name,
            tool_name_aliases=tool_name_aliases,
            policy=tool_name_policy,
        )
    if not isinstance(preserved_function_call.get("args"), dict):
        preserved_function_call["args"] = fallback_arguments
    preserved_part["functionCall"] = preserved_function_call
    return preserved_part


def _read_provider_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    provider_payload = payload.get("provider_payload")
    if not isinstance(provider_payload, dict):
        return None
    return provider_payload
