from __future__ import annotations

from typing import Any, NoReturn

from ..errors import (
    ConfigurationError,
    UpstreamAuthenticationError,
    UpstreamRateLimitError,
    UpstreamServiceError,
    UpstreamTimeoutError,
)

INCOMPLETE_STREAM_MESSAGE = (
    "上游在输出尚未完成时提前停止了这次回复，当前只收到部分内容。"
    "请关闭流式，或切换更稳定的连接后重试。"
)


def build_responses_failed_message(payload: dict[str, Any]) -> str:
    response = payload.get("response")
    if isinstance(response, dict):
        error = response.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return f"LLM streaming request failed: {message.strip()}"
        if isinstance(error, str) and error.strip():
            return f"LLM streaming request failed: {error.strip()}"
        if isinstance(error, list):
            for item in error:
                if isinstance(item, dict):
                    message = item.get("message")
                    if isinstance(message, str) and message.strip():
                        return f"LLM streaming request failed: {message.strip()}"
                if isinstance(item, str) and item.strip():
                    return f"LLM streaming request failed: {item.strip()}"
    return "LLM streaming request failed: response.failed"


def looks_like_openai_chat_payload(payload: dict[str, Any]) -> bool:
    return isinstance(payload.get("choices"), list)


def raise_http_status_error(*, status_code: int, message: str) -> NoReturn:
    if status_code in {401, 403}:
        raise UpstreamAuthenticationError(message)
    if status_code == 429:
        raise UpstreamRateLimitError(message)
    if status_code in {408, 504}:
        raise UpstreamTimeoutError(message)
    if 500 <= status_code <= 599:
        raise UpstreamServiceError(message)
    raise ConfigurationError(message)
