from __future__ import annotations

from typing import Any

from ..errors import ConfigurationError
from .llm_protocol_responses import extract_response_truncation_reason

EMPTY_TOOL_RESPONSE_MESSAGE = (
    "当前连接在启用工具时返回了空响应：既没有文本，也没有工具调用。"
    "这通常表示该连接当前不支持所选协议下的工具调用。"
    "请重新执行“验证工具”，或切换可稳定支持工具调用的连接。"
)
TRUNCATED_RESPONSE_MESSAGE_PREFIX = "上游在输出尚未完成时提前停止了这次回复，"


def raise_if_empty_tool_response(
    *,
    has_tools: bool,
    content: str,
    tool_calls: list[Any],
) -> None:
    if not has_tools:
        return
    if content.strip() or tool_calls:
        return
    raise ConfigurationError(EMPTY_TOOL_RESPONSE_MESSAGE)


def build_truncated_response_message(stop_reason: str) -> str:
    return (
        TRUNCATED_RESPONSE_MESSAGE_PREFIX
        + f"当前只收到部分内容（stop_reason={stop_reason}）。"
        + "请在“模型与连接”里调高单次回复上限，或切换更稳定的连接后重试。"
    )


def raise_if_truncated_response(
    *,
    api_dialect: str,
    payload: dict[str, Any],
) -> None:
    stop_reason = extract_response_truncation_reason(api_dialect, payload)
    if stop_reason is None:
        return
    raise ConfigurationError(build_truncated_response_message(stop_reason))
