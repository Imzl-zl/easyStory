from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
import uuid

from app.shared.runtime.errors import ConfigurationError

from ..assistant_runtime_terminal import (
    AssistantRuntimeTerminalError,
    AssistantRuntimeTerminalPayload,
    resolve_assistant_terminal_payload,
)
from ..tooling.assistant_tool_runtime_dto import AssistantToolLoopStateSnapshot
from .assistant_turn_error_support import AssistantTurnInProgressError
from .assistant_turn_run_store import AssistantTurnRunRecord
from .assistant_turn_runtime_support import (
    AssistantTurnRunSnapshot,
    PreparedAssistantTurn,
    build_completion_messages_digest,
)
from ..dto import AssistantTurnResponseDTO


def recover_existing_turn(
    *,
    prepared: PreparedAssistantTurn,
    existing_run: AssistantTurnRunRecord,
) -> AssistantTurnResponseDTO | None:
    ensure_existing_turn_matches_request(
        prepared=prepared,
        existing_run=existing_run,
    )
    if existing_run.status == "running":
        raise AssistantTurnInProgressError()
    if existing_run.status == "completed":
        if not isinstance(existing_run.response_snapshot, dict):
            raise ConfigurationError(
                "Assistant turn run snapshot is missing response_snapshot for completed run"
            )
        return AssistantTurnResponseDTO.model_validate(existing_run.response_snapshot)
    raise AssistantRuntimeTerminalError(
        code=existing_run.terminal_error_code or "run_already_terminated",
        message=existing_run.terminal_error_message or "当前 run 已结束。",
        terminal_status=existing_run.terminal_status or "failed",
        write_effective=existing_run.write_effective,
    )


def ensure_existing_turn_matches_request(
    *,
    prepared: PreparedAssistantTurn,
    existing_run: AssistantTurnRunRecord,
) -> None:
    expected_hash = prepared.run_snapshot.turn_context_hash
    if existing_run.turn_context_hash and existing_run.turn_context_hash != expected_hash:
        raise AssistantRuntimeTerminalError(
            code="turn_idempotency_conflict",
            message="同一个 client_turn_id 已绑定另一份 turn 请求，请生成新的 client_turn_id 后重试。",
        )


def build_running_turn_record(
    *,
    prepared: PreparedAssistantTurn,
    owner_id: uuid.UUID,
    state_version: int = 1,
    provider_continuation_state: dict[str, Any] | None = None,
    pending_tool_calls_snapshot: tuple[dict[str, Any], ...] = (),
    continuation_request_snapshot: dict[str, Any] | None = None,
    continuation_compaction_snapshot: dict[str, Any] | None = None,
    write_effective: bool = False,
    started_at: datetime | None = None,
    updated_at: datetime | None = None,
    runtime_claim_snapshot: dict[str, Any] | None = None,
) -> AssistantTurnRunRecord:
    snapshot_source = prepared.run_snapshot
    timestamp = started_at or datetime.now(timezone.utc)
    return AssistantTurnRunRecord(
        run_id=prepared.turn_context.run_id,
        owner_id=owner_id,
        project_id=prepared.project_id,
        conversation_id=prepared.turn_context.conversation_id,
        client_turn_id=prepared.turn_context.client_turn_id,
        continuation_anchor_snapshot=snapshot_source.continuation_anchor_snapshot,
        compaction_snapshot=snapshot_source.compaction_snapshot,
        request_messages_digest=prepared.turn_context.messages_digest,
        document_context_snapshot=snapshot_source.document_context_snapshot,
        document_context_recovery_snapshot=snapshot_source.document_context_recovery_snapshot,
        document_context_injection_snapshot=snapshot_source.document_context_injection_snapshot,
        document_context_bindings_snapshot=snapshot_source.document_context_bindings_snapshot,
        tool_guidance_snapshot=snapshot_source.tool_guidance_snapshot,
        tool_catalog_version=snapshot_source.tool_catalog_version,
        requested_write_scope=snapshot_source.requested_write_scope,
        requested_write_targets_snapshot=snapshot_source.requested_write_targets_snapshot,
        normalized_input_items_snapshot=snapshot_source.normalized_input_items_snapshot,
        exposed_tool_names_snapshot=snapshot_source.exposed_tool_names_snapshot,
        resolved_tool_descriptor_snapshot=snapshot_source.resolved_tool_descriptor_snapshot,
        tool_policy_decisions_snapshot=snapshot_source.tool_policy_decisions_snapshot,
        approval_grants_snapshot=snapshot_source.approval_grants_snapshot,
        budget_snapshot=snapshot_source.budget_snapshot,
        turn_context_hash=snapshot_source.turn_context_hash,
        runtime_claim_snapshot=deepcopy(runtime_claim_snapshot),
        state_version=state_version,
        status="running",
        finish_reason=None,
        cancel_state=None,
        provider_continuation_state=deepcopy(provider_continuation_state),
        pending_tool_calls_snapshot=tuple(deepcopy(item) for item in pending_tool_calls_snapshot),
        continuation_request_snapshot=deepcopy(continuation_request_snapshot),
        continuation_compaction_snapshot=deepcopy(continuation_compaction_snapshot),
        terminal_status=None,
        completion_messages_digest=None,
        response_snapshot=None,
        terminal_error_code=None,
        terminal_error_message=None,
        write_effective=write_effective,
        started_at=timestamp,
        updated_at=updated_at or timestamp,
        completed_at=None,
    )


def update_running_turn_record(
    *,
    existing_run: AssistantTurnRunRecord,
    snapshot: AssistantToolLoopStateSnapshot,
    updated_at: datetime | None = None,
) -> AssistantTurnRunRecord:
    timestamp = updated_at or datetime.now(timezone.utc)
    return replace(
        existing_run,
        state_version=existing_run.state_version + 1,
        provider_continuation_state=deepcopy(snapshot.provider_continuation_state),
        pending_tool_calls_snapshot=tuple(
            deepcopy(item)
            for item in snapshot.pending_tool_calls_snapshot
        ),
        normalized_input_items_snapshot=(
            tuple(deepcopy(item) for item in snapshot.normalized_input_items_snapshot)
            if snapshot.normalized_input_items_snapshot is not None
            else existing_run.normalized_input_items_snapshot
        ),
        continuation_request_snapshot=(
            deepcopy(snapshot.continuation_request_snapshot)
            if snapshot.continuation_request_snapshot is not None
            else existing_run.continuation_request_snapshot
        ),
        continuation_compaction_snapshot=(
            deepcopy(snapshot.continuation_compaction_snapshot)
            if snapshot.continuation_compaction_snapshot is not None
            else existing_run.continuation_compaction_snapshot
        ),
        write_effective=existing_run.write_effective or snapshot.write_effective,
        updated_at=timestamp,
    )


def build_terminal_turn_record(
    *,
    prepared: PreparedAssistantTurn,
    owner_id: uuid.UUID,
    existing_run: AssistantTurnRunRecord | None,
    response: AssistantTurnResponseDTO | None = None,
    error: Exception | None = None,
    completed_at: datetime | None = None,
) -> AssistantTurnRunRecord:
    terminal_payload = None if error is None else resolve_terminal_error_payload(error)
    finished_at = completed_at or datetime.now(timezone.utc)
    snapshot_source: AssistantTurnRunRecord | AssistantTurnRunSnapshot
    snapshot_source = existing_run if existing_run is not None else prepared.run_snapshot
    write_effective = (
        (existing_run.write_effective if existing_run is not None else False)
        or (terminal_payload.write_effective if terminal_payload is not None else False)
    )
    completed_status = "completed" if terminal_payload is None else terminal_payload.terminal_status
    return AssistantTurnRunRecord(
        run_id=prepared.turn_context.run_id,
        owner_id=owner_id,
        project_id=prepared.project_id,
        conversation_id=prepared.turn_context.conversation_id,
        client_turn_id=prepared.turn_context.client_turn_id,
        continuation_anchor_snapshot=snapshot_source.continuation_anchor_snapshot,
        compaction_snapshot=snapshot_source.compaction_snapshot,
        request_messages_digest=prepared.turn_context.messages_digest,
        document_context_snapshot=snapshot_source.document_context_snapshot,
        document_context_recovery_snapshot=snapshot_source.document_context_recovery_snapshot,
        document_context_injection_snapshot=snapshot_source.document_context_injection_snapshot,
        document_context_bindings_snapshot=snapshot_source.document_context_bindings_snapshot,
        tool_guidance_snapshot=snapshot_source.tool_guidance_snapshot,
        tool_catalog_version=snapshot_source.tool_catalog_version,
        requested_write_scope=snapshot_source.requested_write_scope,
        requested_write_targets_snapshot=snapshot_source.requested_write_targets_snapshot,
        normalized_input_items_snapshot=snapshot_source.normalized_input_items_snapshot,
        exposed_tool_names_snapshot=snapshot_source.exposed_tool_names_snapshot,
        resolved_tool_descriptor_snapshot=snapshot_source.resolved_tool_descriptor_snapshot,
        tool_policy_decisions_snapshot=snapshot_source.tool_policy_decisions_snapshot,
        approval_grants_snapshot=snapshot_source.approval_grants_snapshot,
        budget_snapshot=snapshot_source.budget_snapshot,
        turn_context_hash=snapshot_source.turn_context_hash,
        runtime_claim_snapshot=(
            deepcopy(existing_run.runtime_claim_snapshot)
            if existing_run is not None
            else None
        ),
        state_version=(existing_run.state_version if existing_run is not None else 0) + 1,
        status=completed_status,
        finish_reason=response.output_meta.finish_reason if response is not None else None,
        cancel_state=(
            {"write_effective": write_effective}
            if terminal_payload is not None and terminal_payload.terminal_status == "cancelled"
            else None
        ),
        provider_continuation_state=(
            deepcopy(existing_run.provider_continuation_state)
            if existing_run is not None
            else None
        ),
        pending_tool_calls_snapshot=(),
        continuation_request_snapshot=(
            deepcopy(existing_run.continuation_request_snapshot)
            if existing_run is not None
            else None
        ),
        continuation_compaction_snapshot=(
            deepcopy(existing_run.continuation_compaction_snapshot)
            if existing_run is not None
            else None
        ),
        terminal_status=completed_status,
        completion_messages_digest=(
            build_completion_messages_digest(
                prepared.turn_context.messages,
                assistant_content=response.content,
            )
            if response is not None
            else None
        ),
        response_snapshot=response.model_dump(mode="json") if response is not None else None,
        terminal_error_code=None if terminal_payload is None else terminal_payload.code,
        terminal_error_message=None if terminal_payload is None else terminal_payload.message,
        write_effective=write_effective,
        started_at=existing_run.started_at if existing_run is not None else finished_at,
        updated_at=finished_at,
        completed_at=finished_at,
    )


def resolve_terminal_error_payload(error: Exception) -> AssistantRuntimeTerminalPayload:
    terminal_payload = resolve_assistant_terminal_payload(error)
    if terminal_payload is not None:
        return terminal_payload
    return AssistantRuntimeTerminalPayload(
        code="runtime_error",
        message=str(error).strip() or "这次回复失败了，请重试。",
        terminal_status="failed",
        write_effective=False,
    )
