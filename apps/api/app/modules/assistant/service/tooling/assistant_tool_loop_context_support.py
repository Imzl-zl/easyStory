from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .assistant_tool_runtime_dto import (
    AssistantToolDescriptor,
    AssistantToolExecutionContext,
    AssistantToolExposureContext,
    AssistantToolLoopStateRecorder,
    AssistantToolLoopStateSnapshot,
    AssistantToolPolicyDecision,
)
from ..dto import AssistantContinuationRequestSnapshotDTO

if TYPE_CHECKING:
    from ..turn.assistant_turn_runtime_support import AssistantTurnContext


def _build_tool_execution_context(
    *,
    turn_context: "AssistantTurnContext",
    owner_id: Any,
    project_id: Any,
    tool_call: dict[str, Any],
    descriptor: AssistantToolDescriptor,
    tool_policy_decision: AssistantToolPolicyDecision | None,
) -> AssistantToolExecutionContext:
    arguments = tool_call.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}
    document_context = (
        turn_context.document_context
        if isinstance(turn_context.document_context, dict)
        else {}
    )
    active_binding = _read_active_document_context_binding(turn_context)
    return AssistantToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        arguments=arguments,
        run_id=turn_context.run_id,
        run_audit_id=_build_tool_run_audit_id(
            turn_context.run_id,
            tool_call_id=str(tool_call["tool_call_id"]),
        ),
        tool_call_id=str(tool_call["tool_call_id"]),
        tool_name=str(tool_call["tool_name"]),
        execution_locus=descriptor.execution_locus,
        requested_write_scope=turn_context.requested_write_scope,
        allowed_target_document_refs=(
            tuple(tool_policy_decision.allowed_target_document_refs)
            if tool_policy_decision is not None
            else tuple(turn_context.requested_write_targets)
        ),
        approval_grant=(
            tool_policy_decision.approval_grant
            if tool_policy_decision is not None
            else None
        ),
        active_document_ref=(
            _read_optional_string(active_binding.get("document_ref"))
            if active_binding is not None
            else _read_optional_string(document_context.get("active_document_ref"))
        ),
        active_binding_version=(
            _read_optional_string(active_binding.get("binding_version"))
            if active_binding is not None
            else _read_optional_string(document_context.get("active_binding_version"))
        ),
        active_buffer_state=_build_active_buffer_state(
            active_binding=active_binding,
            document_context=document_context,
        ),
        document_context_bindings=_read_document_context_bindings(turn_context),
    )


def _build_tool_exposure_context(
    *,
    turn_context: "AssistantTurnContext",
    project_id: Any,
    budget_snapshot: dict[str, Any] | None = None,
) -> AssistantToolExposureContext:
    document_context = (
        turn_context.document_context
        if isinstance(turn_context.document_context, dict)
        else {}
    )
    active_binding = _read_active_document_context_binding(turn_context)
    return AssistantToolExposureContext(
        run_id=getattr(turn_context, "run_id", None),
        project_id=project_id,
        requested_write_scope=turn_context.requested_write_scope,
        allowed_target_document_refs=tuple(turn_context.requested_write_targets),
        tool_catalog_version=getattr(turn_context, "tool_catalog_version", None),
        active_document_ref=(
            _read_optional_string(active_binding.get("document_ref"))
            if active_binding is not None
            else _read_optional_string(document_context.get("active_document_ref"))
        ),
        active_binding_version=(
            _read_optional_string(active_binding.get("binding_version"))
            if active_binding is not None
            else _read_optional_string(document_context.get("active_binding_version"))
        ),
        active_buffer_state=_build_active_buffer_state(
            active_binding=active_binding,
            document_context=document_context,
        ),
        document_context_bindings=_read_document_context_bindings(turn_context),
        budget_snapshot=budget_snapshot,
    )


def _build_pending_tool_calls_snapshot(
    tool_calls: list[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "tool_call_id": tool_call["tool_call_id"],
            "tool_name": tool_call["tool_name"],
            "arguments": tool_call.get("arguments"),
            "arguments_text": tool_call.get("arguments_text"),
            "arguments_error": tool_call.get("arguments_error"),
            "provider_ref": tool_call.get("provider_ref"),
        }
        for tool_call in tool_calls
    )


def _record_tool_loop_state(
    state_recorder: AssistantToolLoopStateRecorder | None,
    *,
    pending_tool_calls_snapshot: tuple[dict[str, Any], ...],
    provider_continuation_state: dict[str, Any] | None,
    normalized_input_items_snapshot: tuple[dict[str, Any], ...] | None,
    continuation_request_snapshot: dict[str, Any] | None,
    continuation_compaction_snapshot: dict[str, Any] | None,
    write_effective: bool,
) -> None:
    if state_recorder is None:
        return
    state_recorder(
        AssistantToolLoopStateSnapshot(
            pending_tool_calls_snapshot=pending_tool_calls_snapshot,
            provider_continuation_state=provider_continuation_state,
            normalized_input_items_snapshot=normalized_input_items_snapshot,
            continuation_request_snapshot=continuation_request_snapshot,
            continuation_compaction_snapshot=continuation_compaction_snapshot,
            write_effective=write_effective,
        )
    )


def _build_continuation_request_snapshot(
    *,
    continuation_items: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    provider_continuation_state: dict[str, Any] | None,
) -> dict[str, Any]:
    snapshot = AssistantContinuationRequestSnapshotDTO(
        continuation_items=[
            item
            for item in continuation_items
            if isinstance(item, dict)
        ],
        provider_continuation_state=provider_continuation_state,
    )
    return snapshot.model_dump(mode="json")


def _read_document_context_bindings(
    turn_context: "AssistantTurnContext",
) -> tuple[dict[str, Any], ...]:
    bindings = getattr(turn_context, "document_context_bindings", None)
    if not isinstance(bindings, list):
        return ()
    return tuple(item for item in bindings if isinstance(item, dict))


def _read_active_document_context_binding(
    turn_context: "AssistantTurnContext",
) -> dict[str, Any] | None:
    for binding in _read_document_context_bindings(turn_context):
        if _read_optional_string(binding.get("selection_role")) == "active":
            return binding
    return None


def _build_active_buffer_state(
    *,
    active_binding: dict[str, Any] | None,
    document_context: dict[str, Any],
) -> dict[str, Any] | None:
    fallback = _read_optional_record(document_context.get("active_buffer_state"))
    if active_binding is None:
        return fallback
    payload: dict[str, Any] = {}
    dirty = _read_optional_bool(active_binding.get("buffer_dirty"))
    if dirty is not None:
        payload["dirty"] = dirty
    base_version = _read_optional_string(active_binding.get("base_version"))
    if base_version:
        payload["base_version"] = base_version
    buffer_hash = _read_optional_string(active_binding.get("buffer_hash"))
    if buffer_hash:
        payload["buffer_hash"] = buffer_hash
    buffer_source = _read_optional_string(active_binding.get("buffer_source"))
    if buffer_source:
        payload["source"] = buffer_source
    if payload:
        return payload
    return None


def _build_tool_run_audit_id(run_id: Any, *, tool_call_id: str) -> str:
    return f"{run_id}:{tool_call_id}"


def _read_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _read_optional_record(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _read_optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None
