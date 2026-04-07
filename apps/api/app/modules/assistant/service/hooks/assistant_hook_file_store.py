from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
import shutil
import uuid

from app.shared.runtime.errors import NotFoundError

from .assistant_hook_dto import AssistantHookCreateDTO, AssistantHookDetailDTO, AssistantHookUpdateDTO
from .assistant_user_hook_support import (
    HOOK_FILE_NAME,
    build_hook_detail,
    build_hook_path,
    build_hook_summary,
    build_runtime_hook,
    create_hook_detail,
    detail_to_record,
    format_hook_document,
    parse_hook_document,
    update_hook_detail,
)


class AssistantHookFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list_user_hooks(self, user_id: uuid.UUID):
        records = [
            parse_hook_document(path, path.read_text(encoding="utf-8"))
            for path in self._iter_hook_files(user_id)
        ]
        sorted_records = sorted(
            records,
            key=lambda item: item.updated_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return [build_hook_summary(record) for record in sorted_records]

    def load_user_hook(self, user_id: uuid.UUID, hook_id: str) -> AssistantHookDetailDTO:
        return build_hook_detail(self._find_user_hook(user_id, hook_id))

    def find_user_hook(self, user_id: uuid.UUID, hook_id: str):
        try:
            return self._find_user_hook(user_id, hook_id)
        except NotFoundError:
            return None

    def create_user_hook(
        self,
        user_id: uuid.UUID,
        payload: AssistantHookCreateDTO,
        *,
        reserved_ids: set[str],
        validate_detail: Callable[[AssistantHookDetailDTO], None] | None = None,
    ) -> AssistantHookDetailDTO:
        detail = create_hook_detail(payload, existing_ids=reserved_ids | self._list_existing_ids(user_id))
        self._write_hook(user_id, detail, validate_detail=validate_detail)
        return self.load_user_hook(user_id, detail.id)

    def update_user_hook(
        self,
        user_id: uuid.UUID,
        hook_id: str,
        payload: AssistantHookUpdateDTO,
        *,
        validate_detail: Callable[[AssistantHookDetailDTO], None] | None = None,
    ) -> AssistantHookDetailDTO:
        current = self.load_user_hook(user_id, hook_id)
        detail = update_hook_detail(hook_id, payload, updated_at=current.updated_at)
        self._write_hook(user_id, detail, validate_detail=validate_detail)
        return self.load_user_hook(user_id, hook_id)

    def delete_user_hook(self, user_id: uuid.UUID, hook_id: str) -> None:
        path = build_hook_path(self.root, user_id, hook_id)
        if not path.exists():
            raise NotFoundError(f"Assistant hook not found: {hook_id}")
        hook_dir = path.parent
        path.unlink()
        if hook_dir.exists():
            shutil.rmtree(hook_dir)

    def _write_hook(
        self,
        user_id: uuid.UUID,
        detail: AssistantHookDetailDTO,
        *,
        validate_detail: Callable[[AssistantHookDetailDTO], None] | None = None,
    ) -> None:
        path = build_hook_path(self.root, user_id, detail.id)
        if validate_detail is not None:
            validate_detail(detail)
        build_runtime_hook(detail_to_record(detail, path=path, updated_at=detail.updated_at))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(format_hook_document(detail), encoding="utf-8")

    def _find_user_hook(self, user_id: uuid.UUID, hook_id: str):
        for path in self._iter_hook_files(user_id):
            record = parse_hook_document(path, path.read_text(encoding="utf-8"))
            if record.id == hook_id:
                return record
        raise NotFoundError(f"Assistant hook not found: {hook_id}")

    def _list_existing_ids(self, user_id: uuid.UUID) -> set[str]:
        return {
            parse_hook_document(path, path.read_text(encoding="utf-8")).id
            for path in self._iter_hook_files(user_id)
        }

    def _iter_hook_files(self, user_id: uuid.UUID):
        hooks_root = self.root / "users" / str(user_id) / "hooks"
        if not hooks_root.exists():
            return []
        return sorted(hooks_root.rglob(HOOK_FILE_NAME))
