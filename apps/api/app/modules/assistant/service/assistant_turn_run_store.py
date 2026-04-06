from __future__ import annotations

from pathlib import Path
import uuid

from .assistant_turn_run_store_support import (
    AssistantTurnRunRecord,
    read_turn_run_record,
    serialize_turn_run_record,
)


class AssistantTurnRunStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save_run(self, record: AssistantTurnRunRecord) -> None:
        target_path = self._resolve_run_path(record.run_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(".tmp")
        tmp_path.write_text(serialize_turn_run_record(record), encoding="utf-8")
        tmp_path.replace(target_path)

    def create_run(self, record: AssistantTurnRunRecord) -> bool:
        target_path = self._resolve_run_path(record.run_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target_path.open("x", encoding="utf-8") as handle:
                handle.write(serialize_turn_run_record(record))
        except FileExistsError:
            return False
        return True

    def get_run(self, run_id: uuid.UUID) -> AssistantTurnRunRecord | None:
        target_path = self._resolve_run_path(run_id)
        if not target_path.exists():
            return None
        return read_turn_run_record(target_path)

    def save_completed_run(self, record: AssistantTurnRunRecord) -> None:
        self.save_run(record)

    def get_completed_run(self, run_id: uuid.UUID) -> AssistantTurnRunRecord | None:
        record = self.get_run(run_id)
        if record is None or record.status != "completed":
            return None
        return record

    def _resolve_run_path(self, run_id: uuid.UUID | str) -> Path:
        return self.root / f"{run_id}.json"
