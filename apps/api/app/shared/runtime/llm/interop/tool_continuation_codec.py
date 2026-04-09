from __future__ import annotations

from typing import Any

from ..llm_protocol_types import LLMGenerateRequest
from .continuation_item_support import (
    build_openai_responses_input as codec_build_openai_responses_input,
    collect_continuation_tool_names as codec_collect_continuation_tool_names,
    read_latest_continuation_items as codec_read_latest_continuation_items,
    read_previous_response_id as codec_read_previous_response_id,
)
from .continuation_prompt_projection import (
    build_prompt_with_continuation as codec_build_prompt_with_continuation,
    serialize_tool_call_arguments as codec_serialize_tool_call_arguments,
)
from .gemini_continuation_codec import (
    project_continuation_to_gemini_contents as codec_project_continuation_to_gemini_contents,
)
from .tool_name_codec import encode_tool_name
from .tool_result_codec import (
    build_anthropic_tool_result_message as codec_build_anthropic_tool_result_message,
    build_openai_chat_tool_result_message as codec_build_openai_chat_tool_result_message,
)


def build_prompt_with_continuation(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> str:
    return codec_build_prompt_with_continuation(
        request,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )


def project_continuation_to_openai_chat_messages(
    items: list[dict[str, Any]],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("item_type")
        if item_type == "message":
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content.strip()})
            continue
        if item_type == "tool_call":
            tool_call_message = _build_openai_chat_tool_call_message(
                item,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_call_message is not None:
                messages.append(tool_call_message)
            continue
        if item_type == "tool_result":
            tool_result_message = codec_build_openai_chat_tool_result_message(
                item,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_result_message is not None:
                messages.append(tool_result_message)
    return messages


def project_continuation_to_anthropic_messages(
    items: list[dict[str, Any]],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("item_type")
        if item_type == "message":
            anthropic_message = _build_anthropic_text_message(item)
            if anthropic_message is not None:
                messages.append(anthropic_message)
            continue
        if item_type == "tool_call":
            tool_call_message = _build_anthropic_tool_call_message(
                item,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_call_message is not None:
                messages.append(tool_call_message)
            continue
        if item_type == "tool_result":
            tool_result_message = codec_build_anthropic_tool_result_message(
                item,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_result_message is not None:
                messages.append(tool_result_message)
    return messages


def project_continuation_to_gemini_contents(
    items: list[dict[str, Any]],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    return codec_project_continuation_to_gemini_contents(
        items,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )


def build_openai_responses_input(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    return codec_build_openai_responses_input(
        request,
        prompt_builder=lambda active_request: build_prompt_with_continuation(
            active_request,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        ),
    )


def read_previous_response_id(state: dict[str, Any] | None) -> str | None:
    return codec_read_previous_response_id(state)


def read_latest_continuation_items(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    return codec_read_latest_continuation_items(request)


def collect_continuation_tool_names(items: list[dict[str, Any]]) -> list[str]:
    return codec_collect_continuation_tool_names(items)


def _build_openai_chat_tool_call_message(
    item: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> dict[str, Any] | None:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    tool_name = payload.get("tool_name")
    call_id = payload.get("tool_call_id") or item.get("call_id")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return None
    if not isinstance(call_id, str) or not call_id.strip():
        return None
    arguments_text = codec_serialize_tool_call_arguments(payload)
    external_tool_name = encode_tool_name(
        tool_name,
        tool_name_aliases=tool_name_aliases,
        policy=tool_name_policy,
    )
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id.strip(),
                "type": "function",
                "function": {
                    "name": external_tool_name,
                    "arguments": arguments_text,
                },
            }
        ],
    }


def _build_anthropic_text_message(item: dict[str, Any]) -> dict[str, Any] | None:
    role = item.get("role")
    content = item.get("content")
    if role not in {"user", "assistant"}:
        return None
    if not isinstance(content, str) or not content.strip():
        return None
    return {
        "role": role,
        "content": [{"type": "text", "text": content.strip()}],
    }


def _build_anthropic_tool_call_message(
    item: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> dict[str, Any] | None:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    tool_name = payload.get("tool_name")
    call_id = payload.get("tool_call_id") or item.get("call_id")
    arguments = payload.get("arguments")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return None
    if not isinstance(call_id, str) or not call_id.strip():
        return None
    external_tool_name = encode_tool_name(
        tool_name,
        tool_name_aliases=tool_name_aliases,
        policy=tool_name_policy,
    )
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": call_id.strip(),
                "name": external_tool_name,
                "input": arguments if isinstance(arguments, dict) else {},
            }
        ],
    }
