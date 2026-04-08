from __future__ import annotations

import json
from typing import Any, Literal
from uuid import uuid4

from ...errors import ConfigurationError
from ..llm_protocol import (
    LLMConnection,
    LLMFunctionToolDefinition,
    LLMGenerateRequest,
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
    allows_provider_continuation_state,
    build_verification_request,
    prepare_generation_request,
    resolve_continuation_support,
)
from ..llm_protocol_types import NormalizedLLMToolCall

ConformanceProbeKind = Literal[
    "text_probe",
    "tool_definition_probe",
    "tool_call_probe",
    "tool_continuation_probe",
]

SUPPORTED_CONFORMANCE_PROBE_KINDS = frozenset(
    {
        "text_probe",
        "tool_definition_probe",
        "tool_call_probe",
        "tool_continuation_probe",
    }
)
CONFORMANCE_PROBE_KIND_RANKS: dict[ConformanceProbeKind, int] = {
    "text_probe": 0,
    "tool_definition_probe": 1,
    "tool_call_probe": 2,
    "tool_continuation_probe": 3,
}

PROBE_MAX_TOKENS = 128
PROBE_TOOL_NAME = "probe.echo_payload"
PROBE_ECHO_ARGUMENT = "ping"
TOOL_DEFINITION_PROBE_SUCCESS_TEXT = "工具定义探测成功。"
TOOL_DEFINITION_PROBE_PROMPT = (
    f"这是工具定义探测。请直接回复：{TOOL_DEFINITION_PROBE_SUCCESS_TEXT}"
    "不要调用任何工具。"
)
TOOL_DEFINITION_PROBE_SYSTEM_PROMPT = "你正在执行模型工具定义兼容性探测。"
TOOL_CALL_PROBE_PROMPT = "这是工具调用探测。请调用本轮唯一可用的工具一次，参数对象必须是 {\"echo\":\"ping\"}。在收到工具结果前，不要直接回答。"
TOOL_CALL_PROBE_SYSTEM_PROMPT = "你正在执行模型工具调用兼容性探测。你必须先调用唯一可用的工具，再等待工具结果。"
TOOL_CONTINUATION_PROBE_PROMPT = (
    "工具结果已返回。请读取刚收到的工具结果中的 echoed 字段，"
    "并严格按格式回答：工具续接成功：<echoed>。"
    "不要再次调用任何工具，也不要添加其他内容。"
)
TOOL_CONTINUATION_PROBE_SYSTEM_PROMPT = "你正在执行模型工具续接兼容性探测。你已经收到工具结果，必须直接给出最终回答。"

PROBE_TOOL_DEFINITION = LLMFunctionToolDefinition(
    name=PROBE_TOOL_NAME,
    description="Tool conformance probe. Echo the provided payload exactly once.",
    parameters={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "echo": {"type": "string", "minLength": 1},
        },
        "required": ["echo"],
    },
    strict=True,
)


def normalize_conformance_probe_kind(probe_kind: str | None) -> ConformanceProbeKind:
    if probe_kind is None:
        return "text_probe"
    normalized = probe_kind.strip()
    if normalized not in SUPPORTED_CONFORMANCE_PROBE_KINDS:
        raise ConfigurationError(f"Unsupported conformance probe kind: {probe_kind}")
    return normalized  # type: ignore[return-value]


def resolve_conformance_probe_kind_rank(
    probe_kind: str | None,
) -> int | None:
    normalized = _normalize_optional_conformance_probe_kind(probe_kind)
    if normalized is None:
        return None
    return CONFORMANCE_PROBE_KIND_RANKS[normalized]


def conformance_probe_kind_satisfies(
    probe_kind: str | None,
    *,
    required_probe_kind: ConformanceProbeKind,
) -> bool:
    probe_rank = resolve_conformance_probe_kind_rank(probe_kind)
    if probe_rank is None:
        return False
    return probe_rank >= CONFORMANCE_PROBE_KIND_RANKS[required_probe_kind]


def promote_conformance_probe_kind(
    current_probe_kind: str | None,
    candidate_probe_kind: str | None,
) -> ConformanceProbeKind | None:
    current = _normalize_optional_conformance_probe_kind(current_probe_kind)
    candidate = _normalize_optional_conformance_probe_kind(candidate_probe_kind)
    if current is None:
        return candidate
    if candidate is None:
        return current
    current_rank = CONFORMANCE_PROBE_KIND_RANKS[current]
    candidate_rank = CONFORMANCE_PROBE_KIND_RANKS[candidate]
    if candidate_rank >= current_rank:
        return candidate
    return current


def build_conformance_probe_request(
    connection: LLMConnection,
    *,
    model_name: str,
    probe_kind: ConformanceProbeKind,
) -> PreparedLLMHttpRequest:
    if probe_kind == "text_probe":
        return build_verification_request(connection)
    if probe_kind == "tool_definition_probe":
        return _build_generate_request(
            connection,
            model_name=model_name,
            prompt=TOOL_DEFINITION_PROBE_PROMPT,
            system_prompt=TOOL_DEFINITION_PROBE_SYSTEM_PROMPT,
        )
    if probe_kind in {"tool_call_probe", "tool_continuation_probe"}:
        return _build_generate_request(
            connection,
            model_name=model_name,
            prompt=TOOL_CALL_PROBE_PROMPT,
            system_prompt=TOOL_CALL_PROBE_SYSTEM_PROMPT,
        )
    raise ConfigurationError(f"Unsupported conformance probe kind: {probe_kind}")


def build_tool_continuation_probe_followup_request(
    connection: LLMConnection,
    *,
    model_name: str,
    initial_response: NormalizedLLMResponse,
    result_echo: str | None = None,
) -> PreparedLLMHttpRequest:
    tool_call = validate_tool_call_probe_response(initial_response)
    resolved_result_echo = result_echo or build_tool_continuation_probe_result_echo()
    continuation_items = _build_tool_probe_continuation_items(
        initial_response=initial_response,
        tool_call=tool_call,
        result_echo=resolved_result_echo,
    )
    continuation_support = resolve_continuation_support(connection.api_dialect)
    provider_continuation_state = _build_provider_continuation_state(
        initial_response=initial_response,
        continuation_items=continuation_items,
        connection=connection,
        continuation_support=continuation_support,
    )
    return prepare_generation_request(
        LLMGenerateRequest(
            connection=connection,
            model_name=model_name,
            prompt=TOOL_CONTINUATION_PROBE_PROMPT,
            system_prompt=TOOL_CONTINUATION_PROBE_SYSTEM_PROMPT,
            response_format="text",
            temperature=0.0,
            max_tokens=PROBE_MAX_TOKENS,
            top_p=1.0,
            tools=[PROBE_TOOL_DEFINITION],
            continuation_items=continuation_items,
            provider_continuation_state=provider_continuation_state,
        )
    )


def validate_tool_definition_probe_response(response: NormalizedLLMResponse) -> None:
    if response.tool_calls:
        raise ConfigurationError("Tool definition probe returned unexpected tool calls")
    content = response.content.strip()
    if content != TOOL_DEFINITION_PROBE_SUCCESS_TEXT:
        raise ConfigurationError(
            "Tool definition probe must return exactly "
            f"'{TOOL_DEFINITION_PROBE_SUCCESS_TEXT}'"
        )


def validate_tool_call_probe_response(response: NormalizedLLMResponse) -> NormalizedLLMToolCall:
    if len(response.tool_calls) != 1:
        raise ConfigurationError(
            f"Tool call probe expected exactly one tool call, got {len(response.tool_calls)}"
        )
    tool_call = response.tool_calls[0]
    if tool_call.tool_name != PROBE_TOOL_NAME:
        raise ConfigurationError(
            f"Tool call probe expected tool '{PROBE_TOOL_NAME}', got '{tool_call.tool_name}'"
        )
    if tool_call.arguments_error is not None:
        raise ConfigurationError(tool_call.arguments_error)
    if tool_call.arguments.get("echo") != PROBE_ECHO_ARGUMENT:
        raise ConfigurationError(
            "Tool call probe expected arguments {'echo': 'ping'}"
        )
    return tool_call


def validate_tool_continuation_probe_response(
    response: NormalizedLLMResponse,
    *,
    expected_echo: str = PROBE_ECHO_ARGUMENT,
) -> None:
    if response.tool_calls:
        raise ConfigurationError("Tool continuation probe returned unexpected follow-up tool calls")
    content = response.content.strip()
    if not content:
        raise ConfigurationError("Tool continuation probe returned empty final content")
    expected_text = render_tool_continuation_probe_success_text(expected_echo)
    if content != expected_text:
        raise ConfigurationError(
            "Tool continuation probe final content must equal exactly "
            f"'{expected_text}'"
        )


def serialize_probe_response(response: NormalizedLLMResponse) -> dict[str, Any]:
    return {
        "content": response.content,
        "tool_calls": [_serialize_tool_call(item) for item in response.tool_calls],
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
        "provider_response_id": response.provider_response_id,
    }


def build_tool_continuation_probe_result_echo() -> str:
    return f"probe-result-{uuid4().hex[:12]}"


def render_tool_continuation_probe_success_text(expected_echo: str) -> str:
    return f"工具续接成功：{expected_echo}。"


def _build_generate_request(
    connection: LLMConnection,
    *,
    model_name: str,
    prompt: str,
    system_prompt: str,
) -> PreparedLLMHttpRequest:
    return prepare_generation_request(
        LLMGenerateRequest(
            connection=connection,
            model_name=model_name,
            prompt=prompt,
            system_prompt=system_prompt,
            response_format="text",
            temperature=0.0,
            max_tokens=PROBE_MAX_TOKENS,
            top_p=1.0,
            tools=[PROBE_TOOL_DEFINITION],
        )
    )


def _build_tool_probe_continuation_items(
    *,
    initial_response: NormalizedLLMResponse,
    tool_call: NormalizedLLMToolCall,
    result_echo: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    content = initial_response.content.strip()
    if content:
        items.append(
            {
                "item_type": "message",
                "role": "assistant",
                "content": content,
            }
        )
    items.append(
        {
            "item_type": "tool_call",
            "call_id": tool_call.tool_call_id,
            "payload": {
                "tool_name": tool_call.tool_name,
                "arguments": dict(tool_call.arguments),
                "arguments_text": tool_call.arguments_text,
                "tool_call_id": tool_call.tool_call_id,
            },
        }
    )
    structured_output = {
        "echoed": result_echo,
        "probe": "tool_continuation_probe",
        "ok": True,
    }
    items.append(
        {
            "item_type": "tool_result",
            "call_id": tool_call.tool_call_id,
            "status": "completed",
            "tool_name": tool_call.tool_name,
            "payload": {
                "tool_name": tool_call.tool_name,
                "structured_output": structured_output,
                "content_items": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            structured_output,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                    }
                ],
            },
        }
    )
    return items


def _build_provider_continuation_state(
    *,
    initial_response: NormalizedLLMResponse,
    continuation_items: list[dict[str, Any]],
    connection: LLMConnection,
    continuation_support,
) -> dict[str, Any] | None:
    if not allows_provider_continuation_state(continuation_support):
        return None
    previous_response_id = initial_response.provider_response_id
    if not isinstance(previous_response_id, str) or not previous_response_id.strip():
        raise ConfigurationError(
            f"{connection.api_dialect} tool continuation probe requires provider_response_id"
        )
    return {
        "previous_response_id": previous_response_id.strip(),
        "latest_items": continuation_items,
    }


def _serialize_tool_call(tool_call: NormalizedLLMToolCall) -> dict[str, Any]:
    payload = dict(tool_call.__dict__)
    if payload.get("arguments_error") is None:
        payload.pop("arguments_error", None)
    return payload


def _normalize_optional_conformance_probe_kind(
    probe_kind: str | None,
) -> ConformanceProbeKind | None:
    if probe_kind is None:
        return None
    normalized = probe_kind.strip()
    if not normalized:
        return None
    return normalize_conformance_probe_kind(normalized)
