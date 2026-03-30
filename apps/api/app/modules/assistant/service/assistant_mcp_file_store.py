from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil
import uuid

from app.shared.runtime.errors import NotFoundError

from .assistant_mcp_dto import AssistantMcpCreateDTO, AssistantMcpDetailDTO, AssistantMcpUpdateDTO
from .assistant_user_mcp_support import (
    MCP_FILE_NAME,
    build_mcp_detail,
    build_mcp_summary,
    build_runtime_mcp,
    build_project_mcp_path,
    build_user_mcp_path,
    create_project_mcp_detail,
    create_user_mcp_detail,
    detail_to_record,
    format_mcp_document,
    parse_mcp_document,
    update_mcp_detail,
)


class AssistantMcpFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list_user_mcp_servers(self, user_id: uuid.UUID):
        return self._list_mcp_servers(self._user_mcp_root(user_id))

    def list_project_mcp_servers(self, project_id: uuid.UUID):
        return self._list_mcp_servers(self._project_mcp_root(project_id))

    def load_user_mcp_server(self, user_id: uuid.UUID, server_id: str) -> AssistantMcpDetailDTO:
        return build_mcp_detail(self._find_user_mcp_server(user_id, server_id))

    def load_project_mcp_server(self, project_id: uuid.UUID, server_id: str) -> AssistantMcpDetailDTO:
        return build_mcp_detail(self._find_project_mcp_server(project_id, server_id))

    def find_user_mcp_server(self, user_id: uuid.UUID, server_id: str):
        try:
            return self._find_user_mcp_server(user_id, server_id)
        except NotFoundError:
            return None

    def find_project_mcp_server(self, project_id: uuid.UUID, server_id: str):
        try:
            return self._find_project_mcp_server(project_id, server_id)
        except NotFoundError:
            return None

    def create_user_mcp_server(
        self,
        user_id: uuid.UUID,
        payload: AssistantMcpCreateDTO,
        *,
        reserved_ids: set[str],
    ) -> AssistantMcpDetailDTO:
        detail = create_user_mcp_detail(
            payload,
            existing_ids=reserved_ids | self._list_existing_ids(self._user_mcp_root(user_id)),
        )
        self._write_mcp(build_user_mcp_path(self.root, user_id, detail.id), detail)
        return self.load_user_mcp_server(user_id, detail.id)

    def create_project_mcp_server(
        self,
        project_id: uuid.UUID,
        payload: AssistantMcpCreateDTO,
        *,
        reserved_ids: set[str],
    ) -> AssistantMcpDetailDTO:
        detail = create_project_mcp_detail(
            payload,
            existing_ids=reserved_ids | self._list_existing_ids(self._project_mcp_root(project_id)),
        )
        self._write_mcp(build_project_mcp_path(self.root, project_id, detail.id), detail)
        return self.load_project_mcp_server(project_id, detail.id)

    def update_user_mcp_server(
        self,
        user_id: uuid.UUID,
        server_id: str,
        payload: AssistantMcpUpdateDTO,
    ) -> AssistantMcpDetailDTO:
        current = self.load_user_mcp_server(user_id, server_id)
        detail = update_mcp_detail(server_id, payload, updated_at=current.updated_at)
        self._write_mcp(build_user_mcp_path(self.root, user_id, detail.id), detail)
        return self.load_user_mcp_server(user_id, server_id)

    def update_project_mcp_server(
        self,
        project_id: uuid.UUID,
        server_id: str,
        payload: AssistantMcpUpdateDTO,
    ) -> AssistantMcpDetailDTO:
        current = self.load_project_mcp_server(project_id, server_id)
        detail = update_mcp_detail(server_id, payload, updated_at=current.updated_at)
        self._write_mcp(build_project_mcp_path(self.root, project_id, detail.id), detail)
        return self.load_project_mcp_server(project_id, server_id)

    def delete_user_mcp_server(self, user_id: uuid.UUID, server_id: str) -> None:
        self._delete_mcp(build_user_mcp_path(self.root, user_id, server_id), server_id)

    def delete_project_mcp_server(self, project_id: uuid.UUID, server_id: str) -> None:
        self._delete_mcp(build_project_mcp_path(self.root, project_id, server_id), server_id)

    def _list_mcp_servers(self, mcp_root: Path):
        records = [parse_mcp_document(path, path.read_text(encoding="utf-8")) for path in self._iter_mcp_files(mcp_root)]
        sorted_records = sorted(
            records,
            key=lambda item: item.updated_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return [build_mcp_summary(record) for record in sorted_records]

    def _write_mcp(self, path: Path, detail: AssistantMcpDetailDTO) -> None:
        build_runtime_mcp(detail_to_record(detail, path=path, updated_at=detail.updated_at))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(format_mcp_document(detail), encoding="utf-8")

    def _find_user_mcp_server(self, user_id: uuid.UUID, server_id: str):
        return self._find_mcp_server(self._user_mcp_root(user_id), server_id)

    def _find_project_mcp_server(self, project_id: uuid.UUID, server_id: str):
        return self._find_mcp_server(self._project_mcp_root(project_id), server_id)

    def _find_mcp_server(self, mcp_root: Path, server_id: str):
        for path in self._iter_mcp_files(mcp_root):
            record = parse_mcp_document(path, path.read_text(encoding="utf-8"))
            if record.id == server_id:
                return record
        raise NotFoundError(f"Assistant MCP not found: {server_id}")

    def _delete_mcp(self, path: Path, server_id: str) -> None:
        if not path.exists():
            raise NotFoundError(f"Assistant MCP not found: {server_id}")
        server_dir = path.parent
        path.unlink()
        if server_dir.exists():
            shutil.rmtree(server_dir)

    def _list_existing_ids(self, mcp_root: Path) -> set[str]:
        return {parse_mcp_document(path, path.read_text(encoding="utf-8")).id for path in self._iter_mcp_files(mcp_root)}

    def _iter_mcp_files(self, mcp_root: Path):
        if not mcp_root.exists():
            return []
        return sorted(mcp_root.rglob(MCP_FILE_NAME))

    def _project_mcp_root(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / "mcp_servers"

    def _user_mcp_root(self, user_id: uuid.UUID) -> Path:
        return self.root / "users" / str(user_id) / "mcp_servers"
