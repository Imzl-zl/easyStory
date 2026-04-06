from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
import uuid

from app.shared.runtime.errors import ConfigurationError

from .assistant_runtime_claim_support import normalize_runtime_claim_snapshot
from .assistant_snapshot_store_support import SnapshotReader, dump_snapshot, load_snapshot_object
from .dto import AssistantCompactionSnapshotDTO, AssistantNormalizedInputItemDTO
AssistantTurnRunStatus = Literal["running", "completed", "failed", "cancelled"]
AssistantTurnTerminalStatus = Literal["completed", "failed", "cancelled"]
ASSISTANT_TURN_RUN_STATUSES = frozenset({"running", "completed", "failed", "cancelled"})
ASSISTANT_REQUESTED_WRITE_SCOPES = frozenset({"disabled", "turn"})
ASSISTANT_TOOL_DESCRIPTOR_ORIGINS = frozenset({"project_document"})
ASSISTANT_TOOL_DESCRIPTOR_TRUST_CLASSES = frozenset({"local_first_party"})
ASSISTANT_TOOL_DESCRIPTOR_PLANES = frozenset({"resource", "mutation"})
ASSISTANT_TOOL_DESCRIPTOR_MUTABILITIES = frozenset({"read_only", "write"})
ASSISTANT_TOOL_DESCRIPTOR_EXECUTION_LOCI = frozenset({"local_runtime", "provider_hosted", "remote_mcp"})
ASSISTANT_TOOL_DESCRIPTOR_APPROVAL_MODES = frozenset({"none", "grant_bound", "always_confirm"})
ASSISTANT_TOOL_DESCRIPTOR_IDEMPOTENCY_CLASSES = frozenset({"safe_read", "conditional_write"})
ASSISTANT_TOOL_VISIBILITIES = frozenset({"hidden", "visible"})
ASSISTANT_TOOL_HIDDEN_REASONS = frozenset(
    {"not_in_project_scope", "unsupported_approval_mode", "write_grant_unavailable"}
)
ASSISTANT_RUN_BUDGET_FIELDS = (
    "max_steps",
    "max_tool_calls",
    "max_input_tokens",
    "max_history_tokens",
    "max_tool_schema_tokens",
    "max_tool_result_tokens_per_step",
    "max_read_bytes",
    "max_write_bytes",
    "max_parallel_tool_calls",
    "tool_timeout_seconds",
)
TURN_RUN_SNAPSHOT_LABEL = "Assistant turn run snapshot"


@dataclass(frozen=True)
class AssistantTurnRunRecord:
    run_id: uuid.UUID
    owner_id: uuid.UUID
    project_id: uuid.UUID | None
    conversation_id: str
    client_turn_id: str
    continuation_anchor_snapshot: dict[str, Any] | None
    compaction_snapshot: dict[str, Any] | None
    request_messages_digest: str
    document_context_snapshot: dict[str, Any] | None
    document_context_bindings_snapshot: tuple[dict[str, Any], ...]
    requested_write_scope: str
    requested_write_targets_snapshot: tuple[str, ...]
    normalized_input_items_snapshot: tuple[dict[str, Any], ...]
    exposed_tool_names_snapshot: tuple[str, ...]
    resolved_tool_descriptor_snapshot: tuple[dict[str, Any], ...]
    tool_policy_decisions_snapshot: tuple[dict[str, Any], ...]
    approval_grants_snapshot: tuple[dict[str, Any], ...]
    budget_snapshot: dict[str, Any] | None
    turn_context_hash: str | None
    runtime_claim_snapshot: dict[str, Any] | None
    state_version: int
    status: AssistantTurnRunStatus
    finish_reason: str | None
    cancel_state: dict[str, Any] | None
    provider_continuation_state: dict[str, Any] | None
    pending_tool_calls_snapshot: tuple[dict[str, Any], ...]
    terminal_status: AssistantTurnTerminalStatus | None
    completion_messages_digest: str | None
    response_snapshot: dict[str, Any] | None
    terminal_error_code: str | None
    terminal_error_message: str | None
    write_effective: bool
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    tool_catalog_version: str | None = None

    def model_dump(self) -> dict[str, object]:
        payload = asdict(self)
        payload["run_id"] = str(self.run_id)
        payload["owner_id"] = str(self.owner_id)
        payload["project_id"] = str(self.project_id) if self.project_id is not None else None
        payload["document_context_bindings_snapshot"] = list(self.document_context_bindings_snapshot)
        payload["requested_write_targets_snapshot"] = list(self.requested_write_targets_snapshot)
        payload["normalized_input_items_snapshot"] = list(self.normalized_input_items_snapshot)
        payload["exposed_tool_names_snapshot"] = list(self.exposed_tool_names_snapshot)
        payload["resolved_tool_descriptor_snapshot"] = list(self.resolved_tool_descriptor_snapshot)
        payload["tool_policy_decisions_snapshot"] = list(self.tool_policy_decisions_snapshot)
        payload["approval_grants_snapshot"] = list(self.approval_grants_snapshot)
        payload["pending_tool_calls_snapshot"] = list(self.pending_tool_calls_snapshot)
        payload["started_at"] = self.started_at.astimezone(UTC).isoformat()
        payload["updated_at"] = self.updated_at.astimezone(UTC).isoformat()
        payload["completed_at"] = (
            self.completed_at.astimezone(UTC).isoformat()
            if self.completed_at is not None
            else None
        )
        return payload


def serialize_turn_run_record(record: AssistantTurnRunRecord) -> str:
    return dump_snapshot(record.model_dump())


def read_turn_run_record(path: Path) -> AssistantTurnRunRecord:
    payload = load_snapshot_object(path, TURN_RUN_SNAPSHOT_LABEL)
    reader = SnapshotReader(TURN_RUN_SNAPSHOT_LABEL, path, quoted_field_name=True)
    status, terminal_status = _resolve_status_fields(payload, reader)
    completion_messages_digest = reader.read_optional_string(payload, "completion_messages_digest")
    if status == "completed" and completion_messages_digest is None:
        completion_messages_digest = reader.read_required_string(payload, "completion_messages_digest")
    completed_at = reader.read_optional_datetime(payload, "completed_at")
    if status == "running" and completed_at is not None:
        raise ConfigurationError(
            f"{TURN_RUN_SNAPSHOT_LABEL} running status cannot include completed_at: {path}"
        )
    if status != "running" and completed_at is None:
        completed_at = reader.read_required_datetime(payload, "completed_at")
    started_at = reader.read_optional_datetime(payload, "started_at") or completed_at
    updated_at = reader.read_optional_datetime(payload, "updated_at") or started_at
    if started_at is None or updated_at is None:
        raise ConfigurationError(
            f"{TURN_RUN_SNAPSHOT_LABEL} must include started_at/updated_at for non-terminal runs: {path}"
        )
    return AssistantTurnRunRecord(
        run_id=reader.read_required_uuid(payload, "run_id"),
        owner_id=reader.read_required_uuid(payload, "owner_id"),
        project_id=reader.read_optional_uuid(payload, "project_id"),
        conversation_id=reader.read_required_string(payload, "conversation_id"),
        client_turn_id=reader.read_required_string(payload, "client_turn_id"),
        continuation_anchor_snapshot=reader.read_optional_object(payload, "continuation_anchor_snapshot"),
        compaction_snapshot=_read_optional_compaction_snapshot(payload, "compaction_snapshot", reader),
        request_messages_digest=reader.read_required_string(payload, "request_messages_digest"),
        document_context_snapshot=reader.read_optional_object(payload, "document_context_snapshot"),
        document_context_bindings_snapshot=reader.read_optional_object_tuple(
            payload,
            "document_context_bindings_snapshot",
        ),
        requested_write_scope=reader.read_optional_literal_string(
            payload,
            "requested_write_scope",
            ASSISTANT_REQUESTED_WRITE_SCOPES,
        )
        or "disabled",
        requested_write_targets_snapshot=reader.read_optional_string_tuple(
            payload,
            "requested_write_targets_snapshot",
        ),
        normalized_input_items_snapshot=_read_optional_normalized_input_items_snapshot(
            payload,
            "normalized_input_items_snapshot",
            reader,
        ),
        exposed_tool_names_snapshot=reader.read_optional_string_tuple(
            payload,
            "exposed_tool_names_snapshot",
        ),
        resolved_tool_descriptor_snapshot=_read_optional_tool_descriptor_snapshot(
            payload,
            "resolved_tool_descriptor_snapshot",
            reader,
        ),
        tool_policy_decisions_snapshot=_read_optional_tool_policy_decision_snapshot(
            payload,
            "tool_policy_decisions_snapshot",
            reader,
        ),
        approval_grants_snapshot=_read_optional_tool_approval_grant_snapshot(
            payload,
            "approval_grants_snapshot",
            reader,
        ),
        budget_snapshot=_read_optional_budget_snapshot(payload, "budget_snapshot", reader),
        turn_context_hash=_read_optional_sha256_string(payload, "turn_context_hash", reader),
        tool_catalog_version=reader.read_optional_string(payload, "tool_catalog_version"),
        runtime_claim_snapshot=_read_optional_runtime_claim_snapshot(
            payload,
            "runtime_claim_snapshot",
            reader,
        ),
        state_version=reader.read_optional_positive_int(payload, "state_version") or 1,
        status=status,
        finish_reason=reader.read_optional_string(payload, "finish_reason"),
        cancel_state=reader.read_optional_object(payload, "cancel_state"),
        provider_continuation_state=reader.read_optional_object(payload, "provider_continuation_state"),
        pending_tool_calls_snapshot=reader.read_optional_object_tuple(
            payload,
            "pending_tool_calls_snapshot",
        ),
        terminal_status=terminal_status,
        completion_messages_digest=completion_messages_digest,
        response_snapshot=reader.read_optional_object(payload, "response_snapshot"),
        terminal_error_code=reader.read_optional_string(payload, "terminal_error_code"),
        terminal_error_message=reader.read_optional_string(payload, "terminal_error_message"),
        write_effective=reader.read_optional_bool(payload, "write_effective") or False,
        started_at=started_at,
        updated_at=updated_at,
        completed_at=completed_at,
    )


def _resolve_status_fields(
    payload: dict[str, object],
    reader: SnapshotReader,
) -> tuple[AssistantTurnRunStatus, AssistantTurnTerminalStatus | None]:
    status = reader.read_optional_literal_string(payload, "status", ASSISTANT_TURN_RUN_STATUSES)
    terminal_status = reader.read_optional_literal_string(
        payload,
        "terminal_status",
        {"completed", "failed", "cancelled"},
    )
    if status is None:
        status = terminal_status or "completed"
    if status == "running":
        if terminal_status is None:
            return status, None
        raise ConfigurationError(
            f"{TURN_RUN_SNAPSHOT_LABEL} running status cannot include terminal_status: {reader.path}"
        )
    if terminal_status is None:
        return status, _resolve_terminal_status_from_status(status)
    return status, terminal_status


def _resolve_terminal_status_from_status(status: AssistantTurnRunStatus) -> AssistantTurnTerminalStatus:
    if status == "completed":
        return "completed"
    if status == "failed":
        return "failed"
    if status == "cancelled":
        return "cancelled"
    raise ConfigurationError(f"{TURN_RUN_SNAPSHOT_LABEL} status '{status}' is not terminal")


def _read_optional_normalized_input_items_snapshot(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> tuple[dict[str, Any], ...]:
    normalized: list[dict[str, Any]] = []
    for item in reader.read_optional_object_tuple(payload, field_name):
        try:
            dto = AssistantNormalizedInputItemDTO.model_validate(item)
        except Exception as exc:
            raise ConfigurationError(
                f"{reader._field_ref(field_name)} contains invalid normalized input item: {reader.path}"
            ) from exc
        normalized.append(dto.model_dump(mode="json"))
    return tuple(normalized)


def _read_optional_compaction_snapshot(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> dict[str, Any] | None:
    value = reader.read_optional_object(payload, field_name)
    if value is None:
        return None
    try:
        dto = AssistantCompactionSnapshotDTO.model_validate(value)
    except Exception as exc:
        raise ConfigurationError(
            f"{reader._field_ref(field_name)} contains invalid compaction snapshot: {reader.path}"
        ) from exc
    return dto.model_dump(mode="json")


def _read_optional_tool_descriptor_snapshot(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        _validate_tool_descriptor_snapshot(item, field_name, reader)
        for item in reader.read_optional_object_tuple(payload, field_name)
    )


def _read_optional_tool_policy_decision_snapshot(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        _validate_tool_policy_decision_snapshot(item, field_name, reader)
        for item in reader.read_optional_object_tuple(payload, field_name)
    )


def _read_optional_tool_approval_grant_snapshot(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        _validate_tool_approval_grant_snapshot(item, field_name, reader)
        for item in reader.read_optional_object_tuple(payload, field_name)
    )


def _read_optional_sha256_string(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> str | None:
    value = reader.read_optional_string(payload, field_name)
    if value is None:
        return None
    if len(value) == 64 and all(char in "0123456789abcdef" for char in value):
        return value
    raise ConfigurationError(
        f"{reader._field_ref(field_name)} must be a sha256 hex string or null: {reader.path}"
    )


def _read_optional_budget_snapshot(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> dict[str, Any] | None:
    budget = reader.read_optional_object(payload, field_name)
    if budget is None:
        return None
    unknown_fields = set(budget) - set(ASSISTANT_RUN_BUDGET_FIELDS)
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise ConfigurationError(
            f"{reader._field_ref(field_name)} contains unknown keys [{unknown_list}]: {reader.path}"
        )
    normalized: dict[str, Any] = {}
    for key in ASSISTANT_RUN_BUDGET_FIELDS:
        if key not in budget:
            raise ConfigurationError(
                f"{reader._field_ref(field_name)} must include '{key}': {reader.path}"
            )
        try:
            if key in {"max_steps", "max_parallel_tool_calls"}:
                normalized[key] = reader.read_required_positive_int(budget, key)
                continue
            normalized[key] = reader.read_optional_positive_int(budget, key)
        except ConfigurationError as exc:
            raise ConfigurationError(
                f"{reader._field_ref(field_name)} contains invalid '{key}': {reader.path}"
            ) from exc
    return normalized


def _read_optional_runtime_claim_snapshot(
    payload: dict[str, object],
    field_name: str,
    reader: SnapshotReader,
) -> dict[str, Any] | None:
    snapshot = reader.read_optional_object(payload, field_name)
    if snapshot is None:
        return None
    return normalize_runtime_claim_snapshot(
        snapshot,
        field_ref=reader._field_ref(field_name),
        path=str(reader.path),
    )


def _validate_tool_descriptor_snapshot(
    item: dict[str, Any],
    field_name: str,
    reader: SnapshotReader,
) -> dict[str, Any]:
    timeout_seconds = reader.read_required_int(item, "timeout_seconds")
    if timeout_seconds < 1:
        raise ConfigurationError(
            f"{reader._field_ref(field_name)} contains invalid timeout_seconds: {reader.path}"
        )
    return {
        "name": reader.read_required_string(item, "name"),
        "description": reader.read_required_string(item, "description"),
        "input_schema": reader.read_required_object(item, "input_schema"),
        "output_schema": reader.read_required_object(item, "output_schema"),
        "origin": reader.read_required_literal_string(
            item,
            "origin",
            ASSISTANT_TOOL_DESCRIPTOR_ORIGINS,
        ),
        "trust_class": reader.read_required_literal_string(
            item,
            "trust_class",
            ASSISTANT_TOOL_DESCRIPTOR_TRUST_CLASSES,
        ),
        "plane": reader.read_required_literal_string(item, "plane", ASSISTANT_TOOL_DESCRIPTOR_PLANES),
        "mutability": reader.read_required_literal_string(
            item,
            "mutability",
            ASSISTANT_TOOL_DESCRIPTOR_MUTABILITIES,
        ),
        "execution_locus": reader.read_required_literal_string(
            item,
            "execution_locus",
            ASSISTANT_TOOL_DESCRIPTOR_EXECUTION_LOCI,
        ),
        "approval_mode": reader.read_required_literal_string(
            item,
            "approval_mode",
            ASSISTANT_TOOL_DESCRIPTOR_APPROVAL_MODES,
        ),
        "idempotency_class": reader.read_required_literal_string(
            item,
            "idempotency_class",
            ASSISTANT_TOOL_DESCRIPTOR_IDEMPOTENCY_CLASSES,
        ),
        "timeout_seconds": timeout_seconds,
    }


def _validate_tool_policy_decision_snapshot(
    item: dict[str, Any],
    field_name: str,
    reader: SnapshotReader,
) -> dict[str, Any]:
    visibility = reader.read_required_literal_string(item, "visibility", ASSISTANT_TOOL_VISIBILITIES)
    hidden_reason = reader.read_optional_literal_string(item, "hidden_reason", ASSISTANT_TOOL_HIDDEN_REASONS)
    if visibility == "visible" and hidden_reason is not None:
        raise ConfigurationError(
            f"{reader._field_ref(field_name)} visible decision cannot include hidden_reason: {reader.path}"
        )
    approval_grant = reader.read_optional_object(item, "approval_grant")
    return {
        "descriptor": _validate_tool_descriptor_snapshot(
            reader.read_required_object(item, "descriptor"),
            f"{field_name}.descriptor",
            reader,
        ),
        "visibility": visibility,
        "effective_approval_mode": reader.read_required_literal_string(
            item,
            "effective_approval_mode",
            ASSISTANT_TOOL_DESCRIPTOR_APPROVAL_MODES,
        ),
        "allowed_target_document_refs": reader.read_optional_string_tuple(item, "allowed_target_document_refs"),
        "approval_grant": (
            None
            if approval_grant is None
            else _validate_tool_approval_grant_snapshot(
                approval_grant,
                f"{field_name}.approval_grant",
                reader,
            )
        ),
        "hidden_reason": hidden_reason,
    }


def _validate_tool_approval_grant_snapshot(
    item: dict[str, Any],
    field_name: str,
    reader: SnapshotReader,
) -> dict[str, Any]:
    return {
        "grant_id": reader.read_required_string(item, "grant_id"),
        "allowed_tool_names": reader.read_optional_string_tuple(item, "allowed_tool_names"),
        "target_document_refs": reader.read_optional_string_tuple(item, "target_document_refs"),
        "binding_version_constraints": reader.read_string_map(
            item,
            "binding_version_constraints",
        ),
        "base_version_constraints": reader.read_string_map(item, "base_version_constraints"),
        "approval_mode_snapshot": reader.read_required_literal_string(
            item,
            "approval_mode_snapshot",
            ASSISTANT_TOOL_DESCRIPTOR_APPROVAL_MODES,
        ),
        "expires_at": reader.read_optional_string(item, "expires_at"),
    }
