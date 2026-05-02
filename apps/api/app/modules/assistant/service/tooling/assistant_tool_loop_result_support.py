from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.runtime.errors import BusinessRuleError

from ..assistant_runtime_terminal import AssistantRuntimeTerminalError
from .assistant_tool_executor import AssistantToolExecutor
from .assistant_tool_runtime_dto import (
    AssistantToolDescriptor,
    AssistantToolExecutionContext,
    AssistantToolLifecycleUpdate,
    AssistantToolResultEnvelope,
)

READ_ONLY_TOOL_TIMEOUT_MAX_RETRIES = 1
RETURN_ERROR_TO_MODEL_CODES = frozenset(
    {
        "binding_version_mismatch",
        "document_not_found",
        "document_not_readable",
        "document_not_writable",
        "edit_operations_required",
        "edit_old_text_required",
        "edit_target_ambiguous",
        "edit_target_not_found",
        "edit_target_overlaps",
        "invalid_arguments",
        "invalid_json",
        "revision_state_mismatch",
        "schema_validation_failed",
        "version_conflict",
        "write_target_mismatch",
    }
)


class AssistantToolStatePersistError(AssistantRuntimeTerminalError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        effective_status: str,
        tool_result: AssistantToolResultEnvelope,
        write_effective: bool,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            terminal_status="failed",
            write_effective=write_effective,
        )
        self.effective_status = effective_status
        self.tool_result = tool_result


def _build_tool_call_start_payload(tool_call: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_call_id": tool_call["tool_call_id"],
        "tool_name": tool_call["tool_name"],
        "target_summary": _build_tool_target_summary(tool_call),
    }


def _build_tool_call_result_payload(
    tool_call: dict[str, Any],
    tool_result: AssistantToolResultEnvelope,
    *,
    descriptor: AssistantToolDescriptor,
) -> dict[str, Any]:
    return {
        "tool_call_id": tool_call["tool_call_id"],
        "tool_name": tool_call["tool_name"],
        "status": _resolve_successful_tool_result_status(
            descriptor=descriptor,
            result=tool_result,
        ),
        "result_summary": _build_tool_result_summary(tool_result),
        "resource_links": tool_result.resource_links,
        "error": tool_result.error,
    }


def _build_failed_tool_call_result_payload(
    tool_call: dict[str, Any],
    error: Exception,
) -> dict[str, Any]:
    status = _resolve_failed_tool_status(error)
    summary = _build_failed_tool_result_summary(error)
    return {
        "tool_call_id": tool_call["tool_call_id"],
        "tool_name": tool_call["tool_name"],
        "status": status,
        "result_summary": summary,
        "resource_links": [],
        "error": _serialize_tool_call_error(error),
    }


def _build_state_persist_failed_tool_call_result_payload(
    tool_call: dict[str, Any],
    error: AssistantToolStatePersistError,
) -> dict[str, Any]:
    summary = _build_tool_result_summary(error.tool_result)
    summary["terminal"] = True
    summary["state_persist_failed"] = True
    summary["error_code"] = error.code
    summary["message"] = str(error)
    return {
        "tool_call_id": tool_call["tool_call_id"],
        "tool_name": tool_call["tool_name"],
        "status": error.effective_status,
        "result_summary": summary,
        "resource_links": error.tool_result.resource_links,
        "error": _serialize_tool_call_error(error),
    }


def _build_cancelled_tool_call_result_payload(
    tool_call: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tool_call_id": tool_call["tool_call_id"],
        "tool_name": tool_call["tool_name"],
        "status": "cancelled",
        "result_summary": _build_cancelled_tool_result_summary(),
        "resource_links": [],
        "error": _build_cancelled_tool_error_payload(),
    }


def _build_tool_target_summary(tool_call: dict[str, Any]) -> dict[str, Any]:
    arguments = tool_call.get("arguments")
    if not isinstance(arguments, dict):
        return {}
    summary: dict[str, Any] = {}
    path = arguments.get("path")
    if isinstance(path, str) and path.strip():
        summary["path"] = path.strip()
    base_version = arguments.get("base_version")
    if isinstance(base_version, str) and base_version.strip():
        summary["base_version"] = base_version.strip()
    path_prefix = arguments.get("path_prefix")
    if isinstance(path_prefix, str) and path_prefix.strip():
        summary["path_prefix"] = path_prefix.strip()
    query = arguments.get("query")
    if isinstance(query, str) and query.strip():
        summary["query"] = query.strip()
    limit = arguments.get("limit")
    if isinstance(limit, int) and limit > 0:
        summary["limit"] = limit
    paths = arguments.get("paths")
    if isinstance(paths, list):
        normalized_paths = [item for item in paths if isinstance(item, str) and item.strip()]
        if normalized_paths:
            summary["paths"] = normalized_paths
            summary["document_count"] = len(normalized_paths)
    for key in ("sources", "schema_ids", "content_states"):
        values = arguments.get(key)
        if not isinstance(values, list):
            continue
        normalized_values = [item.strip() for item in values if isinstance(item, str) and item.strip()]
        if normalized_values:
            summary[key] = normalized_values
    cursors = arguments.get("cursors")
    if isinstance(cursors, list):
        summary["cursor_count"] = len([item for item in cursors if isinstance(item, str) and item.strip()])
    edits = arguments.get("edits")
    if isinstance(edits, list):
        summary["edit_count"] = len([item for item in edits if isinstance(item, dict)])
    return summary


def _build_tool_result_summary(result: AssistantToolResultEnvelope) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "resource_count": len(result.resource_links),
        "content_item_count": len(result.content_items),
    }
    paths = [
        item["path"]
        for item in result.resource_links
        if isinstance(item, dict) and isinstance(item.get("path"), str) and item["path"].strip()
    ]
    if paths:
        summary["paths"] = paths
        summary["document_count"] = len(paths)
    document_revision_id = result.structured_output.get("document_revision_id")
    if isinstance(document_revision_id, str) and document_revision_id.strip():
        summary["document_revision_id"] = document_revision_id
    run_audit_id = result.structured_output.get("run_audit_id")
    if isinstance(run_audit_id, str) and run_audit_id.strip():
        summary["run_audit_id"] = run_audit_id
    if result.error is not None:
        summary["error_code"] = result.error.get("code")
        message = result.error.get("message")
        if isinstance(message, str) and message.strip():
            summary["message"] = message.strip()
        recovery_kind = result.error.get("recovery_kind")
        if isinstance(recovery_kind, str) and recovery_kind.strip():
            summary["recovery_kind"] = recovery_kind.strip()
        retry_count = result.error.get("retry_count")
        if isinstance(retry_count, int) and retry_count > 0:
            summary["retry_count"] = retry_count
    return summary


def _build_failed_tool_result_summary(error: Exception) -> dict[str, Any]:
    error_payload = _serialize_tool_call_error(error)
    summary: dict[str, Any] = {
        "error_code": error_payload["code"],
        "terminal": True,
    }
    message = error_payload.get("message")
    if isinstance(message, str) and message.strip():
        summary["message"] = message
    if getattr(error, "write_effective", False):
        summary["write_effective"] = True
    return summary


def _build_cancelled_tool_result_summary() -> dict[str, Any]:
    error = _build_cancelled_tool_error_payload()
    return {
        "cancelled": True,
        "terminal": True,
        "error_code": error["code"],
        "message": error["message"],
    }


def _serialize_tool_call_error(error: Exception) -> dict[str, Any]:
    payload = {"code": _resolve_tool_step_error_code(error)}
    detail = str(error).strip()
    if detail:
        payload["message"] = detail
    return payload


def _build_cancelled_tool_error_payload() -> dict[str, str]:
    return {
        "code": "cancel_requested",
        "message": "本轮已停止，当前工具未执行。",
    }


def _resolve_failed_tool_status(error: Exception) -> str:
    effective_status = getattr(error, "effective_status", None)
    if isinstance(effective_status, str) and effective_status.strip():
        return effective_status.strip()
    if getattr(error, "write_effective", False):
        return "committed"
    return "failed"


def _resolve_tool_step_error_code(error: Exception) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and code.strip():
        return code
    return error.__class__.__name__


async def _execute_tool_call_with_timeout(
    *,
    db: AsyncSession,
    executor: AssistantToolExecutor,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    on_lifecycle_update: Callable[[AssistantToolLifecycleUpdate], None],
) -> AssistantToolResultEnvelope:
    if descriptor.mutability == "write":
        return await executor.execute(
            db,
            context,
            on_lifecycle_update=on_lifecycle_update,
        )
    retry_count = 0
    while True:
        try:
            return await asyncio.wait_for(
                executor.execute(
                    db,
                    context,
                    on_lifecycle_update=on_lifecycle_update,
                ),
                timeout=descriptor.timeout_seconds,
            )
        except TimeoutError:
            if retry_count >= READ_ONLY_TOOL_TIMEOUT_MAX_RETRIES:
                return _build_timeout_tool_result(
                    context=context,
                    descriptor=descriptor,
                    retry_count=retry_count,
                )
            retry_count += 1


def _build_timeout_tool_result(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    retry_count: int,
) -> AssistantToolResultEnvelope:
    return _build_recoverable_tool_result(
        context=context,
        code="tool_timeout",
        message=f"工具执行超时，已在 {descriptor.timeout_seconds} 秒后停止等待。",
        extra_error_fields={
            "timeout_seconds": descriptor.timeout_seconds,
            "retry_count": retry_count,
        },
    )


def _coerce_recoverable_tool_error(
    *,
    context: AssistantToolExecutionContext,
    error: Exception,
) -> AssistantToolResultEnvelope | None:
    if isinstance(error, ValidationError):
        return _build_recoverable_tool_result(
            context=context,
            code="invalid_arguments",
            message=_build_validation_error_message(error),
        )
    if isinstance(error, ValueError):
        detail = str(error).strip() or "工具参数不合法。"
        return _build_recoverable_tool_result(
            context=context,
            code="invalid_arguments",
            message=detail,
        )
    if isinstance(error, BusinessRuleError):
        code = _resolve_tool_step_error_code(error)
        if code in RETURN_ERROR_TO_MODEL_CODES:
            return _build_recoverable_tool_result(
                context=context,
                code=code,
                message=str(error).strip() or "工具执行失败。",
            )
    return None


def _build_recoverable_tool_result(
    *,
    context: AssistantToolExecutionContext,
    code: str,
    message: str,
    extra_error_fields: dict[str, Any] | None = None,
) -> AssistantToolResultEnvelope:
    error = _build_recoverable_tool_error_payload(code=code, message=message)
    if extra_error_fields:
        error.update(extra_error_fields)
    return AssistantToolResultEnvelope(
        tool_call_id=context.tool_call_id,
        status="errored",
        structured_output={"error": error},
        content_items=[],
        resource_links=[],
        error=error,
        audit=None,
    )


def _build_recoverable_tool_error_payload(*, code: str, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "retryable": False,
        "recovery_hint": _resolve_recoverable_error_hint(code),
        "requires_user_action": code in USER_ACTION_REQUIRED_ERROR_CODES,
        "recovery_kind": "return_error_to_model",
    }


USER_ACTION_REQUIRED_ERROR_CODES = frozenset(
    {
        "binding_version_mismatch",
        "document_not_found",
        "document_not_readable",
        "document_not_writable",
        "edit_target_overlaps",
        "revision_state_mismatch",
        "version_conflict",
        "write_target_mismatch",
    }
)


def _resolve_recoverable_error_hint(code: str) -> str:
    if code == "invalid_arguments":
        return "请按工具参数 schema 重新组织调用参数。"
    if code == "invalid_json":
        return "请输出合法 JSON 后再重试。"
    if code in {"binding_version_mismatch", "revision_state_mismatch", "version_conflict"}:
        return "请先重新读取目标文稿的最新状态，再决定是否继续写入。"
    if code in {"document_not_found", "document_not_readable", "document_not_writable"}:
        return "请重新选择当前项目内存在且可访问的目标文稿。"
    if code == "edit_target_not_found":
        return "请重新读取目标文稿，确认 old_text 和上下文锚点来自当前版本。"
    if code in {"edit_operations_required", "edit_old_text_required"}:
        return "请至少提供一个带 old_text 和 new_text 的编辑操作。"
    if code == "edit_target_ambiguous":
        return "请提供更长 old_text，或补充紧邻的 context_before / context_after。"
    if code == "edit_target_overlaps":
        return "请拆分或重排编辑操作，确保每个编辑目标互不重叠。"
    if code == "schema_validation_failed":
        return "请按目标文稿要求的结构重新生成内容。"
    if code == "write_target_mismatch":
        return "当前只允许写回本轮绑定的活动文稿。"
    return "请根据返回错误调整参数或上下文后再试。"


def _build_validation_error_message(error: ValidationError) -> str:
    issues: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "arguments"
        message = item.get("msg")
        if isinstance(message, str) and message.strip():
            issues.append(f"{location}: {message.strip()}")
    if not issues:
        return "工具参数不合法。"
    return "工具参数不合法：" + "；".join(issues[:3])


def _resolve_successful_tool_result_status(
    *,
    descriptor: AssistantToolDescriptor,
    result: AssistantToolResultEnvelope,
) -> str:
    if descriptor.mutability == "write" and result.status != "errored":
        return "committed"
    return result.status


def _tool_result_committed_write(
    *,
    descriptor: AssistantToolDescriptor,
    result: AssistantToolResultEnvelope,
) -> bool:
    return descriptor.mutability == "write" and result.status != "errored"
