from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
import shutil
import uuid

from app.shared.runtime.errors import NotFoundError

from .assistant_agent_dto import AssistantAgentCreateDTO, AssistantAgentDetailDTO, AssistantAgentUpdateDTO
from .assistant_agent_support import (
    AGENT_FILE_NAME,
    build_agent_detail,
    build_agent_path,
    build_agent_summary,
    build_runtime_agent,
    create_agent_detail,
    detail_to_record,
    format_agent_markdown,
    parse_agent_markdown,
    update_agent_detail,
)


class AssistantAgentFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list_user_agents(self, user_id: uuid.UUID):
        records = [
            parse_agent_markdown(path, path.read_text(encoding="utf-8"))
            for path in self._iter_agent_files(user_id)
        ]
        sorted_records = sorted(
            records,
            key=lambda item: item.updated_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return [build_agent_summary(record) for record in sorted_records]

    def load_user_agent(self, user_id: uuid.UUID, agent_id: str) -> AssistantAgentDetailDTO:
        return build_agent_detail(self._find_user_agent(user_id, agent_id))

    def find_user_agent(self, user_id: uuid.UUID, agent_id: str):
        try:
            return self._find_user_agent(user_id, agent_id)
        except NotFoundError:
            return None

    def create_user_agent(
        self,
        user_id: uuid.UUID,
        payload: AssistantAgentCreateDTO,
        *,
        reserved_ids: set[str],
        validate_detail: Callable[[AssistantAgentDetailDTO], None] | None = None,
    ) -> AssistantAgentDetailDTO:
        detail = create_agent_detail(payload, existing_ids=reserved_ids | self._list_existing_ids(user_id))
        self._write_agent(user_id, detail, validate_detail=validate_detail)
        return self.load_user_agent(user_id, detail.id)

    def update_user_agent(
        self,
        user_id: uuid.UUID,
        agent_id: str,
        payload: AssistantAgentUpdateDTO,
        *,
        validate_detail: Callable[[AssistantAgentDetailDTO], None] | None = None,
    ) -> AssistantAgentDetailDTO:
        current = self.load_user_agent(user_id, agent_id)
        detail = update_agent_detail(agent_id, payload, updated_at=current.updated_at)
        self._write_agent(user_id, detail, validate_detail=validate_detail)
        return self.load_user_agent(user_id, agent_id)

    def delete_user_agent(self, user_id: uuid.UUID, agent_id: str) -> None:
        path = build_agent_path(self.root, user_id, agent_id)
        if not path.exists():
            raise NotFoundError(f"Assistant agent not found: {agent_id}")
        agent_dir = path.parent
        path.unlink()
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

    def _write_agent(
        self,
        user_id: uuid.UUID,
        detail: AssistantAgentDetailDTO,
        *,
        validate_detail: Callable[[AssistantAgentDetailDTO], None] | None = None,
    ) -> None:
        path = build_agent_path(self.root, user_id, detail.id)
        if validate_detail is not None:
            validate_detail(detail)
        build_runtime_agent(detail_to_record(detail, path=path, updated_at=detail.updated_at))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(format_agent_markdown(detail), encoding="utf-8")

    def _find_user_agent(self, user_id: uuid.UUID, agent_id: str):
        for path in self._iter_agent_files(user_id):
            record = parse_agent_markdown(path, path.read_text(encoding="utf-8"))
            if record.id == agent_id:
                return record
        raise NotFoundError(f"Assistant agent not found: {agent_id}")

    def _list_existing_ids(self, user_id: uuid.UUID) -> set[str]:
        return {parse_agent_markdown(path, path.read_text(encoding="utf-8")).id for path in self._iter_agent_files(user_id)}

    def _iter_agent_files(self, user_id: uuid.UUID):
        agents_root = self.root / "users" / str(user_id) / "agents"
        if not agents_root.exists():
            return []
        return sorted(agents_root.rglob(AGENT_FILE_NAME))
