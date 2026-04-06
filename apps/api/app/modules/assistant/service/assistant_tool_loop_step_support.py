from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from .assistant_tool_runtime_dto import (
    AssistantToolDescriptor,
    AssistantToolExecutionContext,
    AssistantToolLifecycleUpdate,
    AssistantToolResultEnvelope,
)
from .assistant_tool_step_store import AssistantToolStepRecord
from .assistant_tool_loop_result_support import (
    AssistantToolStatePersistError,
    _build_cancelled_tool_error_payload,
    _build_cancelled_tool_result_summary,
    _build_failed_tool_result_summary,
    _build_tool_result_summary,
    _resolve_failed_tool_status,
)


def _build_started_tool_step_record(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    step_index: int,
    started_at: datetime,
) -> AssistantToolStepRecord:
    return _build_tool_step_record(
        context=context,
        descriptor=descriptor,
        step_index=step_index,
        status=_resolve_started_tool_step_status(descriptor),
        started_at=started_at,
        completed_at=None,
        target_document_refs=_resolve_tool_step_target_document_refs(context=context),
        result_summary=None,
        result_hash=None,
        error_code=None,
    )


def _build_completed_tool_step_record(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    step_index: int,
    started_at: datetime,
    result: AssistantToolResultEnvelope,
) -> AssistantToolStepRecord:
    return _build_tool_step_record(
        context=context,
        descriptor=descriptor,
        step_index=step_index,
        status=_resolve_terminal_tool_step_status(descriptor, result=result),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        target_document_refs=_resolve_tool_step_target_document_refs(
            context=context,
            result=result,
        ),
        result_summary=_build_tool_result_summary(result),
        result_hash=_build_json_hash(result.structured_output),
        error_code=_read_tool_result_error_code(result),
    )


def _build_progress_tool_step_record(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    step_index: int,
    started_at: datetime,
    update: AssistantToolLifecycleUpdate,
) -> AssistantToolStepRecord:
    return _build_tool_step_record(
        context=context,
        descriptor=descriptor,
        step_index=step_index,
        status=update.status,
        started_at=started_at,
        completed_at=None,
        target_document_refs=update.target_document_refs or _resolve_tool_step_target_document_refs(context=context),
        result_summary=update.result_summary,
        result_hash=update.result_hash,
        error_code=None,
    )


def _build_failed_tool_step_record(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    step_index: int,
    started_at: datetime,
    error: Exception,
) -> AssistantToolStepRecord:
    return _build_tool_step_record(
        context=context,
        descriptor=descriptor,
        step_index=step_index,
        status=_resolve_failed_tool_step_status(descriptor=descriptor, error=error),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        target_document_refs=_resolve_tool_step_target_document_refs(context=context),
        result_summary=_build_failed_tool_result_summary(error),
        result_hash=None,
        error_code=_resolve_tool_step_error_code(error),
    )


def _build_cancelled_tool_step_record(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    step_index: int,
    started_at: datetime,
) -> AssistantToolStepRecord:
    error = _build_cancelled_tool_error_payload()
    return _build_tool_step_record(
        context=context,
        descriptor=descriptor,
        step_index=step_index,
        status="cancelled",
        started_at=started_at,
        completed_at=datetime.now(UTC),
        target_document_refs=_resolve_tool_step_target_document_refs(context=context),
        result_summary=_build_cancelled_tool_result_summary(),
        result_hash=None,
        error_code=error["code"],
    )


def _build_tool_step_record(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
    step_index: int,
    status: str,
    started_at: datetime,
    completed_at: datetime | None,
    target_document_refs: tuple[str, ...],
    result_summary: dict[str, Any] | None,
    result_hash: str | None,
    error_code: str | None,
) -> AssistantToolStepRecord:
    arguments_hash = _build_json_hash(context.arguments)
    return AssistantToolStepRecord(
        run_id=context.run_id,
        tool_call_id=context.tool_call_id,
        step_index=step_index,
        tool_name=context.tool_name,
        descriptor_hash=_build_json_hash(asdict(descriptor)),
        normalized_arguments_snapshot=context.arguments,
        arguments_hash=arguments_hash,
        target_document_refs=target_document_refs,
        approval_state=_resolve_tool_step_approval_state(
            context=context,
            descriptor=descriptor,
        ),
        approval_grant_id=(
            context.approval_grant.grant_id
            if context.approval_grant is not None
            else None
        ),
        approval_grant_snapshot=_build_approval_grant_snapshot(context),
        status=status,
        dedupe_key=f"{context.run_id}:{context.tool_name}:{context.tool_call_id}:{arguments_hash}",
        idempotency_key=_resolve_tool_step_idempotency_key(context, target_document_refs),
        result_summary=result_summary,
        result_hash=result_hash,
        error_code=error_code,
        started_at=started_at,
        completed_at=completed_at,
    )


def _build_approval_grant_snapshot(
    context: AssistantToolExecutionContext,
) -> dict[str, Any] | None:
    approval_grant = context.approval_grant
    if approval_grant is None:
        return None
    return {
        "grant_id": approval_grant.grant_id,
        "allowed_tool_names": list(approval_grant.allowed_tool_names),
        "target_document_refs": list(approval_grant.target_document_refs),
        "binding_version_constraints": dict(approval_grant.binding_version_constraints),
        "base_version_constraints": dict(approval_grant.base_version_constraints),
        "approval_mode_snapshot": approval_grant.approval_mode_snapshot,
        "expires_at": approval_grant.expires_at,
    }


def _build_tool_state_persist_error(
    *,
    descriptor: AssistantToolDescriptor,
    result: AssistantToolResultEnvelope,
    cause: Exception,
) -> AssistantToolStatePersistError:
    cause_detail = str(cause).strip()
    if descriptor.plane == "mutation":
        message = "文稿写入已生效，但运行时未能完成 committed 状态落盘。请刷新当前文稿确认最新内容。"
        code = "committed_state_persist_failed"
        effective_status = "committed"
        write_effective = True
    else:
        message = "工具结果已产生，但运行时未能完成结果状态落盘。"
        code = "tool_result_state_persist_failed"
        effective_status = "completed"
        write_effective = False
    if cause_detail:
        message = f"{message} 底层错误：{cause_detail}"
    return AssistantToolStatePersistError(
        code=code,
        message=message,
        effective_status=effective_status,
        tool_result=result,
        write_effective=write_effective,
    )


def _resolve_started_tool_step_status(descriptor: AssistantToolDescriptor) -> str:
    if descriptor.plane == "resource":
        return "reading"
    if descriptor.plane == "mutation":
        return "validating"
    return "queued"


def _resolve_terminal_tool_step_status(
    descriptor: AssistantToolDescriptor,
    *,
    result: AssistantToolResultEnvelope,
) -> str:
    if result.status == "errored":
        return "failed"
    if descriptor.plane == "mutation":
        return "committed"
    return "completed"


def _resolve_failed_tool_step_status(
    *,
    descriptor: AssistantToolDescriptor,
    error: Exception,
) -> str:
    if descriptor.plane == "mutation" and getattr(error, "write_effective", False):
        return _resolve_failed_tool_status(error)
    return "failed"


def _resolve_tool_step_approval_state(
    *,
    context: AssistantToolExecutionContext,
    descriptor: AssistantToolDescriptor,
) -> str:
    if descriptor.approval_mode == "none":
        return "not_required"
    if descriptor.approval_mode == "grant_bound":
        approval_grant = context.approval_grant
        if approval_grant is None:
            return "pending"
        if descriptor.name not in approval_grant.allowed_tool_names:
            return "pending"
        return "approved"
    return "pending"


def _resolve_tool_step_target_document_refs(
    *,
    context: AssistantToolExecutionContext,
    result: AssistantToolResultEnvelope | None = None,
) -> tuple[str, ...]:
    if result is not None:
        refs = [
            item.get("document_ref")
            for item in result.resource_links
            if isinstance(item, dict)
        ]
        normalized = [
            item
            for item in refs
            if isinstance(item, str) and item.strip()
        ]
        if normalized:
            return tuple(dict.fromkeys(normalized))
    if context.tool_name == "project.write_document" and context.active_document_ref is not None:
        return (context.active_document_ref,)
    return ()


def _resolve_tool_step_idempotency_key(
    context: AssistantToolExecutionContext,
    target_document_refs: tuple[str, ...],
) -> str | None:
    if context.tool_name != "project.write_document" or not target_document_refs:
        return None
    return f"{context.run_id}:{context.tool_call_id}:{target_document_refs[0]}"


def _resolve_tool_step_error_code(error: Exception) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and code.strip():
        return code
    return error.__class__.__name__


def _read_tool_result_error_code(result: AssistantToolResultEnvelope) -> str | None:
    if not isinstance(result.error, dict):
        return None
    code = result.error.get("code")
    if isinstance(code, str) and code.strip():
        return code.strip()
    return None


def _build_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
