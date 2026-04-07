from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .llm_interop_profiles import resolve_interop_capabilities
from .llm_protocol import NormalizedLLMResponse
from .llm_protocol_responses import parse_stream_terminal_response


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
) -> ParsedStreamEvent:
    capabilities = resolve_interop_capabilities(api_dialect, interop_profile)
    stop_reason = extract_stream_stop_reason(api_dialect, event_name, payload)
    return ParsedStreamEvent(
        event_name=event_name,
        payload=payload,
        delta=extract_stream_delta(api_dialect, event_name, payload),
        reasoning_delta=extract_stream_reasoning_delta(
            api_dialect,
            event_name,
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
    event_name: str | None,
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
) -> NormalizedLLMResponse | None:
    terminal_payload = _extract_terminal_payload(api_dialect, event_name, payload)
    if terminal_payload is None:
        return None
    return parse_stream_terminal_response(
        api_dialect,
        terminal_payload,
        interop_profile=interop_profile,
    )


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
