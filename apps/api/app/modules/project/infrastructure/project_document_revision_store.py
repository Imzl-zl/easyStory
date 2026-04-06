from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from contextlib import contextmanager
import json
import uuid

from app.shared.runtime.errors import ConfigurationError

from .file_atomic_support import append_text_line, exclusive_file_lock


PROJECT_DOCUMENT_REVISION_LOG_FILE = ".document_revisions.jsonl"
PROJECT_DOCUMENT_REVISION_LOCK_FILE = ".document_revisions.lock"


@dataclass(frozen=True)
class ProjectDocumentRevisionRecord:
    document_ref: str
    document_revision_id: str
    content_hash: str
    version: str
    created_at: datetime
    run_audit_id: str

    def model_dump(self) -> dict[str, object]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.astimezone(UTC).isoformat()
        return payload


class ProjectDocumentRevisionStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    @contextmanager
    def revision_lock(self, project_id: uuid.UUID):
        with exclusive_file_lock(self._resolve_lock_path(project_id)):
            yield

    def append_revision(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str,
        content_hash: str,
        version: str,
        run_audit_id: str,
    ) -> ProjectDocumentRevisionRecord:
        with self.revision_lock(project_id):
            return self.append_revision_unlocked(
                project_id,
                document_ref=document_ref,
                content_hash=content_hash,
                version=version,
                run_audit_id=run_audit_id,
            )

    def append_revision_unlocked(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str,
        content_hash: str,
        version: str,
        run_audit_id: str,
    ) -> ProjectDocumentRevisionRecord:
        existing = self._get_revision_by_run_audit_id_unlocked(
            project_id,
            document_ref=document_ref,
            run_audit_id=run_audit_id,
        )
        if existing is not None:
            if existing.version != version or existing.content_hash != content_hash:
                raise ConfigurationError(
                    "Project document revision log contains conflicting revision for the same run_audit_id"
                )
            return existing
        record = ProjectDocumentRevisionRecord(
            document_ref=document_ref,
            document_revision_id=str(uuid.uuid4()),
            content_hash=content_hash,
            version=version,
            created_at=datetime.now(UTC),
            run_audit_id=run_audit_id,
        )
        target_path = self._resolve_log_path(project_id)
        append_text_line(
            target_path,
            json.dumps(record.model_dump(), ensure_ascii=False, sort_keys=True),
        )
        return record

    def get_revision_by_run_audit_id(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str,
        run_audit_id: str,
    ) -> ProjectDocumentRevisionRecord | None:
        with self.revision_lock(project_id):
            return self._get_revision_by_run_audit_id_unlocked(
                project_id,
                document_ref=document_ref,
                run_audit_id=run_audit_id,
            )

    def get_latest_revision(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str,
    ) -> ProjectDocumentRevisionRecord | None:
        with self.revision_lock(project_id):
            for record in reversed(self._list_revisions_unlocked(project_id, document_ref=document_ref)):
                return record
            return None

    def list_revisions(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str | None = None,
    ) -> tuple[ProjectDocumentRevisionRecord, ...]:
        with self.revision_lock(project_id):
            return self._list_revisions_unlocked(project_id, document_ref=document_ref)

    def _get_revision_by_run_audit_id_unlocked(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str,
        run_audit_id: str,
    ) -> ProjectDocumentRevisionRecord | None:
        for record in reversed(self._list_revisions_unlocked(project_id, document_ref=document_ref)):
            if record.run_audit_id == run_audit_id:
                return record
        return None

    def _list_revisions_unlocked(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str | None = None,
    ) -> tuple[ProjectDocumentRevisionRecord, ...]:
        target_path = self._resolve_log_path(project_id)
        if not target_path.exists():
            return ()
        records: list[ProjectDocumentRevisionRecord] = []
        for line in target_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ConfigurationError(
                    f"Project document revision log contains invalid JSON: {target_path}"
                ) from exc
            if not isinstance(payload, dict):
                raise ConfigurationError(
                    f"Project document revision log entry must be an object: {target_path}"
                )
            record = ProjectDocumentRevisionRecord(
                document_ref=_read_required_string(payload, "document_ref", target_path),
                document_revision_id=_read_required_string(
                    payload, "document_revision_id", target_path
                ),
                content_hash=_read_required_string(payload, "content_hash", target_path),
                version=_read_required_string(payload, "version", target_path),
                created_at=_read_required_datetime(payload, "created_at", target_path),
                run_audit_id=_read_required_string(payload, "run_audit_id", target_path),
            )
            if document_ref is not None and record.document_ref != document_ref:
                continue
            records.append(record)
        return tuple(records)

    def _resolve_log_path(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / PROJECT_DOCUMENT_REVISION_LOG_FILE

    def _resolve_lock_path(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / PROJECT_DOCUMENT_REVISION_LOCK_FILE


def _read_required_string(payload: dict[str, object], field_name: str, path: Path) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    raise ConfigurationError(
        f"Project document revision log field '{field_name}' must be a non-empty string: {path}"
    )


def _read_required_datetime(payload: dict[str, object], field_name: str, path: Path) -> datetime:
    raw_value = _read_required_string(payload, field_name, path)
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"Project document revision log field '{field_name}' must be an ISO datetime: {path}"
        ) from exc
