from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urlsplit

from .errors import ConfigurationError
from .gemini_probe_support import apply_gemini_probe_thinking_config
from .llm_endpoint_policy import normalize_custom_base_url
from .llm_protocol_types import (
    ANTHROPIC_VERSION,
    DEFAULT_BASE_URLS,
    JSON_OBJECT_RESPONSE_FORMAT,
    LLMConnection,
    LLMGenerateRequest,
    PreparedLLMHttpRequest,
    VERIFY_MAX_TOKENS,
    VERIFY_SYSTEM_PROMPT,
    VERIFY_USER_PROMPT,
    normalize_api_dialect,
    resolve_api_key_header_name,
    resolve_auth_strategy,
    resolve_model_name,
)

USER_AGENT_HEADER_NAME = "User-Agent"
RUNTIME_KIND_LABELS = {
    "server-python": "server; python",
    "server-node": "server; node",
    "browser": "browser",
}


def prepare_generation_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    dialect = normalize_api_dialect(request.connection.api_dialect)
    if dialect == "openai_chat_completions":
        return _build_openai_chat_request(request)
    if dialect == "openai_responses":
        return _build_openai_responses_request(request)
    if dialect == "anthropic_messages":
        return _build_anthropic_messages_request(request)
    return _build_gemini_generate_content_request(request)


def build_verification_request(connection: LLMConnection) -> PreparedLLMHttpRequest:
    model_name = resolve_model_name(
        requested_model_name=None,
        default_model=connection.default_model,
        provider_label="credential verification",
    )
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=connection,
            model_name=model_name,
            prompt=VERIFY_USER_PROMPT,
            system_prompt=VERIFY_SYSTEM_PROMPT,
            response_format="text",
            temperature=0.0,
            max_tokens=VERIFY_MAX_TOKENS,
            top_p=1.0,
        )
    )
    if normalize_api_dialect(connection.api_dialect) == "gemini_generate_content":
        return apply_gemini_probe_thinking_config(request, model_name)
    return request


def _build_openai_chat_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "messages": _build_openai_chat_messages(request),
    }
    if request.tools:
        body["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "strict": tool.strict,
                },
            }
            for tool in request.tools
        ]
        body["parallel_tool_calls"] = False
    _merge_generation_params(body, request)
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        body["response_format"] = {"type": "json_object"}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/chat/completions"),
        headers=_build_request_headers(request.connection),
        json_body=body,
    )


def _build_openai_responses_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "input": _build_openai_responses_input(request),
    }
    previous_response_id = _read_previous_response_id(request.provider_continuation_state)
    if previous_response_id is not None:
        body["previous_response_id"] = previous_response_id
    if request.tools:
        body["tools"] = [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "strict": tool.strict,
            }
            for tool in request.tools
        ]
        body["parallel_tool_calls"] = False
    if request.system_prompt:
        body["instructions"] = request.system_prompt
    _merge_generation_params(body, request, max_tokens_field="max_output_tokens")
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        body["text"] = {"format": {"type": "json_object"}}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/responses"),
        headers=_build_request_headers(request.connection),
        json_body=body,
    )


def _build_anthropic_messages_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "max_tokens": request.max_tokens or 1024,
        "messages": _build_anthropic_messages(request),
    }
    if request.tools:
        body["tools"] = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in request.tools
        ]
    if request.system_prompt:
        body["system"] = [{"type": "text", "text": request.system_prompt}]
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.top_p is not None:
        body["top_p"] = request.top_p
    if request.stop:
        body["stop_sequences"] = request.stop
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/messages"),
        headers=_build_request_headers(
            request.connection,
            extra_headers={"anthropic-version": ANTHROPIC_VERSION},
        ),
        json_body=body,
    )


def _build_gemini_generate_content_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "contents": _build_gemini_contents(request),
    }
    generation_config = _build_gemini_generation_config(request)
    if generation_config:
        body["generationConfig"] = generation_config
    if request.tools:
        body["tools"] = [
            {
                "functionDeclarations": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                    for tool in request.tools
                ]
            }
        ]
    if request.system_prompt:
        body["system_instruction"] = {"parts": [{"text": request.system_prompt}]}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_build_gemini_endpoint(request.connection, request.model_name),
        headers=_build_request_headers(request.connection),
        json_body=body,
    )


def _build_openai_chat_messages(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    if request.prompt.strip():
        messages.append({"role": "user", "content": request.prompt})
    messages.extend(_project_continuation_to_openai_chat_messages(request.continuation_items))
    return messages


def _build_anthropic_messages(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if request.prompt.strip():
        messages.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": request.prompt}],
            }
        )
    messages.extend(_project_continuation_to_anthropic_messages(request.continuation_items))
    return messages


def _build_gemini_contents(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    if request.prompt.strip():
        contents.append({"role": "user", "parts": [{"text": request.prompt}]})
    contents.extend(_project_continuation_to_gemini_contents(request.continuation_items))
    return contents


def _build_prompt_with_continuation(request: LLMGenerateRequest) -> str:
    continuation_projection = _render_continuation_items_as_text(request.continuation_items)
    if continuation_projection is None:
        return request.prompt
    if not request.prompt.strip():
        return continuation_projection
    return f"{request.prompt}\n\n{continuation_projection}"


def _render_continuation_items_as_text(items: list[dict[str, Any]]) -> str | None:
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
                sections.append(
                    "\n".join(
                        [
                            "【工具调用】",
                            f"名称：{tool_name.strip()}",
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


def _project_continuation_to_openai_chat_messages(
    items: list[dict[str, Any]],
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
            tool_call_message = _build_openai_chat_tool_call_message(item)
            if tool_call_message is not None:
                messages.append(tool_call_message)
            continue
        if item_type == "tool_result":
            tool_result_message = _build_openai_chat_tool_result_message(item)
            if tool_result_message is not None:
                messages.append(tool_result_message)
    return messages


def _build_openai_chat_tool_call_message(item: dict[str, Any]) -> dict[str, Any] | None:
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
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id.strip(),
                "type": "function",
                "function": {
                    "name": tool_name.strip(),
                    "arguments": arguments_text,
                },
            }
        ],
    }


def _build_openai_chat_tool_result_message(item: dict[str, Any]) -> dict[str, Any] | None:
    call_id = item.get("call_id")
    payload = item.get("payload")
    if not isinstance(call_id, str) or not call_id.strip():
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "role": "tool",
        "tool_call_id": call_id.strip(),
        "content": _serialize_tool_result_payload(item, payload),
    }


def _project_continuation_to_anthropic_messages(
    items: list[dict[str, Any]],
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
            tool_call_message = _build_anthropic_tool_call_message(item)
            if tool_call_message is not None:
                messages.append(tool_call_message)
            continue
        if item_type == "tool_result":
            tool_result_message = _build_anthropic_tool_result_message(item)
            if tool_result_message is not None:
                messages.append(tool_result_message)
    return messages


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


def _build_anthropic_tool_call_message(item: dict[str, Any]) -> dict[str, Any] | None:
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
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": call_id.strip(),
                "name": tool_name.strip(),
                "input": arguments if isinstance(arguments, dict) else {},
            }
        ],
    }


def _build_anthropic_tool_result_message(item: dict[str, Any]) -> dict[str, Any] | None:
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
                "content": _serialize_tool_result_payload(item, payload),
            }
        ],
    }


def _project_continuation_to_gemini_contents(
    items: list[dict[str, Any]],
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
            tool_call_content, tool_name = _build_gemini_tool_call_content(item)
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
            )
            if tool_result_content is not None:
                contents.append(tool_result_content)
    return contents


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
) -> tuple[dict[str, Any] | None, str | None]:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None, None
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return None, None
    arguments = payload.get("arguments")
    return (
        {
            "role": "model",
            "parts": [
                {
                    "functionCall": {
                        "name": tool_name.strip(),
                        "args": arguments if isinstance(arguments, dict) else {},
                    }
                }
            ],
        },
        tool_name.strip(),
    )


def _build_gemini_tool_result_content(
    item: dict[str, Any],
    *,
    tool_name_by_call_id: dict[str, str],
) -> dict[str, Any] | None:
    payload = item.get("payload")
    call_id = item.get("call_id")
    if not isinstance(payload, dict):
        return None
    if not isinstance(call_id, str) or not call_id.strip():
        return None
    tool_name = tool_name_by_call_id.get(call_id.strip())
    if tool_name is None:
        tool_name = _read_tool_result_tool_name(item, payload)
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
) -> str | None:
    candidates = (item.get("tool_name"), payload.get("tool_name"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
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
) -> str:
    result_payload = dict(payload)
    tool_name = _read_tool_result_tool_name(item, payload)
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


def _build_openai_responses_input(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    previous_response_id = _read_previous_response_id(request.provider_continuation_state)
    if previous_response_id is not None:
        return _build_openai_responses_continuation_input(request)
    prompt = _build_prompt_with_continuation(request)
    return [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}],
        }
    ]


def _read_previous_response_id(state: dict[str, Any] | None) -> str | None:
    if not isinstance(state, dict):
        return None
    value = state.get("previous_response_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _read_latest_continuation_items(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    state = request.provider_continuation_state
    if isinstance(state, dict):
        latest_items = state.get("latest_items")
        if isinstance(latest_items, list):
            return [item for item in latest_items if isinstance(item, dict)]
    return [item for item in request.continuation_items if isinstance(item, dict)]


def _build_openai_responses_continuation_input(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    continuation_items = _read_latest_continuation_items(request)
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


def _build_gemini_generation_config(request: LLMGenerateRequest) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if request.temperature is not None:
        config["temperature"] = request.temperature
    if request.max_tokens is not None:
        config["maxOutputTokens"] = request.max_tokens
    if request.top_p is not None:
        config["topP"] = request.top_p
    if request.stop:
        config["stopSequences"] = request.stop
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        config["responseMimeType"] = "application/json"
    return config


def _merge_generation_params(
    body: dict[str, Any],
    request: LLMGenerateRequest,
    *,
    max_tokens_field: str = "max_tokens",
) -> None:
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.max_tokens is not None:
        body[max_tokens_field] = request.max_tokens
    if request.top_p is not None:
        body["top_p"] = request.top_p
    if request.stop:
        body["stop"] = request.stop


def _join_endpoint(connection: LLMConnection, endpoint: str) -> str:
    base_url = _resolve_base_url(connection)
    normalized_base = base_url.rstrip("/")
    endpoint_path = "/" + endpoint.lstrip("/")
    base_path = _resolve_base_path(normalized_base)
    if base_path.endswith(endpoint_path):
        return normalized_base
    if base_path.endswith("/v1") and endpoint_path.startswith("/v1/"):
        return f"{normalized_base}/{endpoint_path.removeprefix('/v1/')}"
    if base_path.endswith("/v1beta") and endpoint_path.startswith("/v1beta/"):
        return f"{normalized_base}/{endpoint_path.removeprefix('/v1beta/')}"
    return f"{normalized_base}{endpoint_path}"


def _build_gemini_endpoint(connection: LLMConnection, model_name: str) -> str:
    base_url = _resolve_base_url(connection).rstrip("/")
    if base_url.endswith(":generateContent"):
        return base_url
    endpoint = f"/v1beta/models/{quote(model_name, safe='')}:generateContent"
    return _join_endpoint(connection, endpoint)


def _resolve_base_url(connection: LLMConnection) -> str:
    custom_base_url = normalize_custom_base_url(connection.base_url)
    if custom_base_url is not None:
        return custom_base_url
    return DEFAULT_BASE_URLS[normalize_api_dialect(connection.api_dialect)]


def _resolve_base_path(base_url: str) -> str:
    path = urlsplit(base_url).path.rstrip("/")
    return path or "/"


def _build_request_headers(
    connection: LLMConnection,
    *,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = dict(connection.extra_headers or {})
    headers["Content-Type"] = "application/json"
    headers.update(_build_auth_headers(connection))
    user_agent = _build_user_agent(connection)
    if user_agent is not None:
        headers[USER_AGENT_HEADER_NAME] = user_agent
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _build_user_agent(connection: LLMConnection) -> str | None:
    if connection.user_agent_override is not None:
        return connection.user_agent_override
    if connection.client_name is None:
        return None
    user_agent = connection.client_name
    if connection.client_version:
        user_agent = f"{user_agent}/{connection.client_version}"
    if connection.runtime_kind:
        user_agent = f"{user_agent} ({RUNTIME_KIND_LABELS[connection.runtime_kind]})"
    return user_agent


def _build_auth_headers(connection: LLMConnection) -> dict[str, str]:
    strategy = resolve_auth_strategy(connection.api_dialect, connection.auth_strategy)
    if strategy == "bearer":
        return {"Authorization": f"Bearer {connection.api_key}"}
    header_name = resolve_api_key_header_name(
        api_dialect=connection.api_dialect,
        auth_strategy=connection.auth_strategy,
        api_key_header_name=connection.api_key_header_name,
    )
    if header_name is None:
        raise ConfigurationError("Missing API key header name for auth strategy")
    return {header_name: connection.api_key}
