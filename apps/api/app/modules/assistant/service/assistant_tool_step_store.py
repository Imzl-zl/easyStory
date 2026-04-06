from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import os
from typing import Any, Literal
from urllib.parse import quote, unquote
import uuid

from app.shared.runtime.errors import ConfigurationError

from .assistant_snapshot_store_support import SnapshotReader, dump_snapshot, load_snapshot_object

AssistantToolStepApprovalState = Literal["not_required", "pending", "approved", "rejected", "expired"]
AssistantToolStepStatus = Literal[
    "queued",
    "reading",
    "validating",
    "writing",
    "committed",
    "completed",
    "failed",
    "cancelled",
]
ASSISTANT_TOOL_STEP_APPROVAL_STATES = frozenset({"not_required", "pending", "approved", "rejected", "expired"})
ASSISTANT_TOOL_STEP_STATUSES = frozenset(
    {"queued", "reading", "validating", "writing", "committed", "completed", "failed", "cancelled"}
)
TOOL_STEP_SNAPSHOT_LABEL = "Assistant tool step snapshot"


@dataclass(frozen=True)
class AssistantToolStepRecord:
    run_id: uuid.UUID
    tool_call_id: str
    step_index: int
    tool_name: str
    descriptor_hash: str
    normalized_arguments_snapshot: dict[str, Any]
    arguments_hash: str
    target_document_refs: tuple[str, ...]
    approval_state: AssistantToolStepApprovalState
    approval_grant_id: str | None
    status: AssistantToolStepStatus
    dedupe_key: str
    idempotency_key: str | None
    result_summary: dict[str, Any] | None
    result_hash: str | None
    error_code: str | None
    started_at: datetime
    completed_at: datetime | None
    approval_grant_snapshot: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        _validate_step_approval_state(self.approval_state)
        _validate_step_status(self.status)

    def model_dump(self) -> dict[str, object]:
        payload = asdict(self)
        payload["run_id"] = str(self.run_id)
        payload["target_document_refs"] = list(self.target_document_refs)
        payload["started_at"] = self.started_at.astimezone(UTC).isoformat()
        payload["completed_at"] = (
            self.completed_at.astimezone(UTC).isoformat()
            if self.completed_at is not None
            else None
        )
        return payload


class AssistantToolStepStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def append_step(self, record: AssistantToolStepRecord) -> None:
        step_dir = self._resolve_step_dir(record.run_id, record.tool_call_id)
        step_dir.mkdir(parents=True, exist_ok=True)
        payload = dump_snapshot(record.model_dump())
        sequence = self._read_next_sequence(step_dir)
        while True:
            target_path = step_dir / f"{sequence:04d}.json"
            try:
                with target_path.open("x", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                return
            except FileExistsError:
                sequence += 1

    def get_latest_step(
        self,
        run_id: uuid.UUID,
        tool_call_id: str,
    ) -> AssistantToolStepRecord | None:
        records = self.list_step_history(run_id, tool_call_id)
        return records[-1] if records else None

    def list_latest_steps(self, run_id: uuid.UUID) -> list[AssistantToolStepRecord]:
        run_dir = self.root / str(run_id)
        if not run_dir.exists():
            return []
        latest_records: list[AssistantToolStepRecord] = []
        for entry in sorted(run_dir.iterdir(), key=lambda item: item.name):
            if not entry.is_dir():
                continue
            tool_call_id = unquote(entry.name)
            latest = self.get_latest_step(run_id, tool_call_id)
            if latest is not None:
                latest_records.append(latest)
        return sorted(latest_records, key=lambda item: item.step_index)

    def list_step_history(
        self,
        run_id: uuid.UUID,
        tool_call_id: str,
    ) -> list[AssistantToolStepRecord]:
        step_dir = self._resolve_step_dir(run_id, tool_call_id)
        if not step_dir.exists():
            return []
        return [
            self._read_record(path)
            for path in sorted(step_dir.glob("*.json"), key=lambda item: item.name)
        ]

    def _resolve_step_dir(self, run_id: uuid.UUID, tool_call_id: str) -> Path:
        return self.root / str(run_id) / quote(tool_call_id, safe="")

    def _read_next_sequence(self, step_dir: Path) -> int:
        max_sequence = 0
        for path in step_dir.glob("*.json"):
            try:
                sequence = int(path.stem)
            except ValueError:
                continue
            if sequence > max_sequence:
                max_sequence = sequence
        return max_sequence + 1

    def _read_record(self, path: Path) -> AssistantToolStepRecord:
        payload = load_snapshot_object(path, TOOL_STEP_SNAPSHOT_LABEL)
        reader = SnapshotReader(
            TOOL_STEP_SNAPSHOT_LABEL,
            path,
            normalize_datetimes_to_utc=True,
        )
        return AssistantToolStepRecord(
            run_id=reader.read_required_uuid(payload, "run_id"),
            tool_call_id=reader.read_required_string(payload, "tool_call_id", strip=False),
            step_index=reader.read_required_int(payload, "step_index"),
            tool_name=reader.read_required_string(payload, "tool_name", strip=False),
            descriptor_hash=reader.read_required_string(payload, "descriptor_hash", strip=False),
            normalized_arguments_snapshot=reader.read_required_object(
                payload,
                "normalized_arguments_snapshot",
            ),
            arguments_hash=reader.read_required_string(payload, "arguments_hash", strip=False),
            target_document_refs=reader.read_required_string_tuple(
                payload,
                "target_document_refs",
                strip=False,
            ),
            approval_state=reader.read_required_literal_string(
                payload,
                "approval_state",
                ASSISTANT_TOOL_STEP_APPROVAL_STATES,
                strip=False,
            ),
            approval_grant_id=reader.read_optional_string(payload, "approval_grant_id", strip=False),
            approval_grant_snapshot=reader.read_optional_object(payload, "approval_grant_snapshot"),
            status=reader.read_required_literal_string(
                payload,
                "status",
                ASSISTANT_TOOL_STEP_STATUSES,
                strip=False,
            ),
            dedupe_key=reader.read_required_string(payload, "dedupe_key", strip=False),
            idempotency_key=reader.read_optional_string(payload, "idempotency_key", strip=False),
            result_summary=reader.read_optional_object(payload, "result_summary"),
            result_hash=reader.read_optional_string(payload, "result_hash", strip=False),
            error_code=reader.read_optional_string(payload, "error_code", strip=False),
            started_at=reader.read_required_datetime(payload, "started_at"),
            completed_at=reader.read_optional_datetime(payload, "completed_at"),
        )


def _validate_step_approval_state(value: str) -> None:
    if value in ASSISTANT_TOOL_STEP_APPROVAL_STATES:
        return
    allowed = ", ".join(sorted(ASSISTANT_TOOL_STEP_APPROVAL_STATES))
    raise ConfigurationError(f"Assistant tool step approval_state must be one of [{allowed}]")


def _validate_step_status(value: str) -> None:
    if value in ASSISTANT_TOOL_STEP_STATUSES:
        return
    allowed = ", ".join(sorted(ASSISTANT_TOOL_STEP_STATUSES))
    raise ConfigurationError(f"Assistant tool step status must be one of [{allowed}]")
