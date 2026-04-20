from __future__ import annotations

from typing import Any

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
    return "LLM streaming request failed: response.failed"


def looks_like_openai_chat_payload(payload: dict[str, Any]) -> bool:
    return isinstance(payload.get("choices"), list)
