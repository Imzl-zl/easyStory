from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Literal

from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError

AssistantRunTerminalStatus = Literal["completed", "failed", "cancelled"]
CANCEL_REQUESTED_ERROR_CODE = "cancel_requested"
CANCEL_REQUESTED_MESSAGE = "本轮已停止。"
CANCEL_REQUESTED_WITH_EFFECTIVE_WRITE_MESSAGE = "本轮已停止，但已有写入生效。"
ASSISTANT_STREAM_ERROR_META_MARKER = "_assistant_stream_error_meta"


class AssistantRuntimeTerminalError(BusinessRuleError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        terminal_status: AssistantRunTerminalStatus = "failed",
        write_effective: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.terminal_status = terminal_status
        self.write_effective = write_effective


@dataclass(frozen=True)
class AssistantRuntimeTerminalPayload:
    code: str
    message: str
    terminal_status: AssistantRunTerminalStatus
    write_effective: bool

    def model_dump(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "terminal_status": self.terminal_status,
            "write_effective": self.write_effective,
        }


def build_cancel_requested_terminal_error(
    *,
    write_effective: bool,
) -> AssistantRuntimeTerminalError:
    return AssistantRuntimeTerminalError(
        code=CANCEL_REQUESTED_ERROR_CODE,
        message=(
            CANCEL_REQUESTED_WITH_EFFECTIVE_WRITE_MESSAGE
            if write_effective
            else CANCEL_REQUESTED_MESSAGE
        ),
        terminal_status="cancelled",
        write_effective=write_effective,
    )


def resolve_assistant_terminal_payload(error: Exception) -> AssistantRuntimeTerminalPayload | None:
    for resolver in (
        _resolve_terminal_payload_from_exact_error,
        _resolve_terminal_payload_from_business_error,
        _resolve_terminal_payload_from_configuration_error,
    ):
        for candidate in _iterate_terminal_error_candidates(error):
            payload = resolver(candidate)
            if payload is not None:
                return payload
    return None


def attach_assistant_stream_error_meta(error: Exception, meta: dict[str, Any]) -> Exception:
    setattr(error, ASSISTANT_STREAM_ERROR_META_MARKER, meta)
    return error


def resolve_assistant_stream_error_meta(error: Exception) -> dict[str, Any] | None:
    for candidate in _iterate_terminal_error_candidates(error):
        meta = getattr(candidate, ASSISTANT_STREAM_ERROR_META_MARKER, None)
        if isinstance(meta, dict):
            return meta
    return None


def _iterate_terminal_error_candidates(error: Exception) -> list[Exception]:
    queue: deque[Exception] = deque([error])
    seen: set[int] = set()
    resolved: list[Exception] = []
    while queue:
        current = queue.popleft()
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        resolved.append(current)
        if isinstance(current, BaseExceptionGroup):
            nested = [
                item
                for item in current.exceptions
                if isinstance(item, Exception)
            ]
            queue.extendleft(reversed(nested))
        if isinstance(current.__cause__, Exception):
            queue.append(current.__cause__)
        if isinstance(current.__context__, Exception) and current.__context__ is not current.__cause__:
            queue.append(current.__context__)
    return resolved


def _resolve_terminal_payload_from_exact_error(
    error: Exception,
) -> AssistantRuntimeTerminalPayload | None:
    if isinstance(error, AssistantRuntimeTerminalError):
        return AssistantRuntimeTerminalPayload(
            code=error.code,
            message=str(error),
            terminal_status=error.terminal_status,
            write_effective=error.write_effective,
        )
    if isinstance(error, StreamInterruptedError):
        return AssistantRuntimeTerminalPayload(
            code=CANCEL_REQUESTED_ERROR_CODE,
            message=CANCEL_REQUESTED_MESSAGE,
            terminal_status="cancelled",
            write_effective=False,
        )
    return None


def _resolve_terminal_payload_from_business_error(
    error: Exception,
) -> AssistantRuntimeTerminalPayload | None:
    if isinstance(error, BusinessRuleError):
        terminal_status = getattr(error, "terminal_status", "failed")
        if terminal_status not in {"completed", "failed", "cancelled"}:
            terminal_status = "failed"
        return AssistantRuntimeTerminalPayload(
            code=getattr(error, "code", "business_rule_error"),
            message=str(error).strip() or "这次回复失败了，请重试。",
            terminal_status=terminal_status,
            write_effective=bool(getattr(error, "write_effective", False)),
        )
    return None


def _resolve_terminal_payload_from_configuration_error(
    error: Exception,
) -> AssistantRuntimeTerminalPayload | None:
    if isinstance(error, ConfigurationError):
        return AssistantRuntimeTerminalPayload(
            code="configuration_error",
            message=str(error).strip() or "这次回复失败了，请检查模型连接后重试。",
            terminal_status="failed",
            write_effective=False,
        )
    return None
