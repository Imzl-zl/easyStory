from __future__ import annotations

import json
from typing import Any

from ...errors import ConfigurationError
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
            tool_result_message = _build_openai_chat_tool_result_message(
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
            tool_result_message = _build_anthropic_tool_result_message(
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
    contents: list[dict[str, Any]] = []
    tool_name_by_call_id: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("item_type")
        if item_type == "message":
            gemini_text_content = _build_gemini_text_content(item)
            if gemini_text_content is not None:
                contents.append(gemini_text_content)
            continue
        if item_type == "tool_call":
            tool_call_content, tool_name = _build_gemini_tool_call_content(
                item,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_call_content is None or tool_name is None:
                continue
            call_id = item.get("call_id")
            if isinstance(call_id, str) and call_id.strip():
                tool_name_by_call_id[call_id.strip()] = tool_name
            contents.append(tool_call_content)
            continue
        if item_type == "tool_result":
            tool_result_content = _build_gemini_tool_result_content(
                item,
                tool_name_by_call_id=tool_name_by_call_id,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=tool_name_policy,
            )
            if tool_result_content is not None:
                contents.append(tool_result_content)
    return contents


def build_openai_responses_input(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    previous_response_id = read_previous_response_id(request.provider_continuation_state)
    if previous_response_id is not None:
        return _build_openai_responses_continuation_input(request)
    prompt = build_prompt_with_continuation(
        request,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )
    return [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}],
        }
    ]


def read_previous_response_id(state: dict[str, Any] | None) -> str | None:
    if not isinstance(state, dict):
        return None
    value = state.get("previous_response_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def read_latest_continuation_items(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    state = request.provider_continuation_state
    if isinstance(state, dict):
        latest_items = state.get("latest_items")
        if isinstance(latest_items, list):
            return [item for item in latest_items if isinstance(item, dict)]
    return [item for item in request.continuation_items if isinstance(item, dict)]


def collect_continuation_tool_names(items: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload = item.get("payload")
        if item.get("item_type") == "tool_call" and isinstance(payload, dict):
            tool_name = payload.get("tool_name")
            if isinstance(tool_name, str) and tool_name.strip():
                names.append(tool_name.strip())
            continue
        if item.get("item_type") != "tool_result" or not isinstance(payload, dict):
            continue
        tool_name = item.get("tool_name")
        if isinstance(tool_name, str) and tool_name.strip():
            names.append(tool_name.strip())
            continue
        payload_tool_name = payload.get("tool_name")
        if isinstance(payload_tool_name, str) and payload_tool_name.strip():
            names.append(payload_tool_name.strip())
    return names


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
            payload = item.get("payload")
            if not isinstance(payload, dict):
                continue
            tool_name = payload.get("tool_name")
            arguments = payload.get("arguments")
            call_id = payload.get("tool_call_id") or item.get("call_id")
            if isinstance(tool_name, str) and tool_name.strip():
                external_tool_name = encode_tool_name(
                    tool_name,
                    tool_name_aliases=tool_name_aliases,
                    policy=tool_name_policy,
                )
                sections.append(
                    "\n".join(
                        [
                            "【工具调用】",
                            f"名称：{external_tool_name}",
                            f"调用 ID：{call_id}" if isinstance(call_id, str) and call_id.strip() else "",
                            f"参数：{json.dumps(arguments, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}",
                        ]
                    ).strip()
                )
            continue
        if item_type == "tool_result":
            payload = item.get("payload")
            if not isinstance(payload, dict):
                continue
            status = item.get("status")
            content_sections = _render_tool_result_payload_as_text(payload)
            if content_sections:
                sections.append(
                    "\n".join(
                        [
                            "【工具结果】",
                            f"状态：{status}" if isinstance(status, str) and status.strip() else "",
                            content_sections,
                        ]
                    ).strip()
                )
    normalized = "\n\n".join(section for section in sections if section.strip())
    return normalized or None


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
    arguments_text = _serialize_tool_call_arguments(payload)
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


def _build_openai_chat_tool_result_message(
    item: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> dict[str, Any] | None:
    call_id = item.get("call_id")
    payload = item.get("payload")
    if not isinstance(call_id, str) or not call_id.strip():
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "role": "tool",
        "tool_call_id": call_id.strip(),
        "content": _serialize_tool_result_payload(
            item,
            payload,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        ),
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


def _build_anthropic_tool_result_message(
    item: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> dict[str, Any] | None:
    call_id = item.get("call_id")
    payload = item.get("payload")
    if not isinstance(call_id, str) or not call_id.strip():
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": call_id.strip(),
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
) -> tuple[dict[str, Any] | None, str | None]:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None, None
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return None, None
    arguments = payload.get("arguments")
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
        external_tool_name,
    )


def _build_gemini_tool_result_content(
    item: dict[str, Any],
    *,
    tool_name_by_call_id: dict[str, str],
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> dict[str, Any] | None:
    payload = item.get("payload")
    call_id = item.get("call_id")
    if not isinstance(payload, dict):
        return None
    if not isinstance(call_id, str) or not call_id.strip():
        return None
    tool_name = tool_name_by_call_id.get(call_id.strip())
    if tool_name is None:
        tool_name = _read_tool_result_tool_name(
            item,
            payload,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
    if tool_name is None:
        return None
    return {
        "role": "user",
        "parts": [
            {
                "functionResponse": {
                    "name": tool_name,
                    "response": _build_gemini_tool_result_response(item, payload),
                }
            }
        ],
    }


def _build_gemini_tool_result_response(
    item: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = dict(payload)
    response["call_id"] = item.get("call_id")
    status = item.get("status")
    if isinstance(status, str) and status.strip():
        response["status"] = status.strip()
    return response


def _read_tool_result_tool_name(
    item: dict[str, Any],
    payload: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> str | None:
    candidates = (item.get("tool_name"), payload.get("tool_name"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return encode_tool_name(
                candidate,
                tool_name_aliases=tool_name_aliases,
                policy=tool_name_policy,
            )
    return None


def _serialize_tool_call_arguments(payload: dict[str, Any]) -> str:
    arguments_text = payload.get("arguments_text")
    if isinstance(arguments_text, str) and arguments_text.strip():
        return arguments_text
    return json.dumps(
        payload.get("arguments") or {},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _serialize_tool_result_payload(
    item: dict[str, Any],
    payload: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> str:
    result_payload = dict(payload)
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


def _build_openai_responses_continuation_input(
    request: LLMGenerateRequest,
) -> list[dict[str, Any]]:
    continuation_items = read_latest_continuation_items(request)
    tool_outputs = _build_openai_responses_function_call_outputs(continuation_items)
    if tool_outputs:
        return tool_outputs
    raise ConfigurationError(
        "OpenAI responses continuation requires tool_result items with call_id and structured_output "
        "when previous_response_id is supplied"
    )


def _build_openai_responses_function_call_outputs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for item in items:
        if item.get("item_type") != "tool_result":
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        call_id = item.get("call_id")
        if not isinstance(call_id, str) or not call_id.strip():
            continue
        structured_output = payload.get("structured_output")
        if structured_output is None:
            continue
        output_text = json.dumps(
            structured_output,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        outputs.append(
            {
                "type": "function_call_output",
                "call_id": call_id.strip(),
                "output": output_text,
            }
        )
    return outputs
