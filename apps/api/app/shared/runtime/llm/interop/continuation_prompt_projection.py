from __future__ import annotations

import json
from typing import Any

from ..llm_protocol_types import LLMGenerateRequest
from .tool_name_codec import encode_tool_name


def build_prompt_with_continuation(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> str:
    continuation_projection = _render_continuation_items_as_text(
        request.continuation_items,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )
    if continuation_projection is None:
        return request.prompt
    if not request.prompt.strip():
        return continuation_projection
    return f"{request.prompt}\n\n{continuation_projection}"


def serialize_tool_call_arguments(payload: dict[str, Any]) -> str:
    arguments_text = payload.get("arguments_text")
    if isinstance(arguments_text, str) and arguments_text.strip():
        return arguments_text
    return json.dumps(
        payload.get("arguments") or {},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _render_continuation_items_as_text(
    items: list[dict[str, Any]],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> str | None:
    sections: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("item_type")
        if item_type == "message":
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str) and content.strip():
                sections.append(f"【上一轮{role}消息】\n{content.strip()}")
            continue
        if item_type == "tool_call":
            tool_call_section = _render_tool_call_as_text(
                item,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_call_section is not None:
                sections.append(tool_call_section)
            continue
        if item_type != "tool_result":
            continue
        tool_result_section = _render_tool_result_as_text(item)
        if tool_result_section is not None:
            sections.append(tool_result_section)
    normalized = "\n\n".join(section for section in sections if section.strip())
    return normalized or None


def _render_tool_call_as_text(
    item: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> str | None:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return None
    call_id = payload.get("tool_call_id") or item.get("call_id")
    arguments = payload.get("arguments")
    external_tool_name = encode_tool_name(
        tool_name,
        tool_name_aliases=tool_name_aliases,
        policy=tool_name_policy,
    )
    return "\n".join(
        [
            "【工具调用】",
            f"名称：{external_tool_name}",
            f"调用 ID：{call_id}" if isinstance(call_id, str) and call_id.strip() else "",
            f"参数：{json.dumps(arguments, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}",
        ]
    ).strip()


def _render_tool_result_as_text(item: dict[str, Any]) -> str | None:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    status = item.get("status")
    content_sections = _render_tool_result_payload_as_text(payload)
    if not content_sections:
        return None
    return "\n".join(
        [
            "【工具结果】",
            f"状态：{status}" if isinstance(status, str) and status.strip() else "",
            content_sections,
        ]
    ).strip()


def _render_tool_result_payload_as_text(payload: dict[str, Any]) -> str:
    content_items = payload.get("content_items")
    lines: list[str] = []
    if isinstance(content_items, list):
        for item in content_items:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(text.strip())
    error = payload.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        message = error.get("message")
        parts: list[str] = []
        if isinstance(code, str) and code.strip():
            parts.append(f"code={code.strip()}")
        if isinstance(message, str) and message.strip():
            parts.append(message.strip())
        if parts:
            lines.append("工具错误：" + " | ".join(parts))
    structured_output = payload.get("structured_output")
    if not lines and structured_output is not None:
        return json.dumps(structured_output, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "\n\n".join(lines)
