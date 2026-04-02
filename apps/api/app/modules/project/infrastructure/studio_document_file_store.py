from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import uuid

from app.shared.runtime.errors import BusinessRuleError


@dataclass(frozen=True)
class ProjectDocumentFileRecord:
    path: str
    content: str
    updated_at: datetime


class ProjectDocumentFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def find_project_document(
        self,
        project_id: uuid.UUID,
        document_path: str,
    ) -> ProjectDocumentFileRecord | None:
        resolved = self._resolve_project_document_path(project_id, document_path)
        if not resolved.exists():
            return None
        stats = resolved.stat()
        return ProjectDocumentFileRecord(
            path=document_path,
            content=resolved.read_text(encoding="utf-8"),
            updated_at=datetime.fromtimestamp(stats.st_mtime, tz=UTC),
        )

    def save_project_document(
        self,
        project_id: uuid.UUID,
        document_path: str,
        content: str,
    ) -> ProjectDocumentFileRecord:
        resolved = self._resolve_project_document_path(project_id, document_path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        stats = resolved.stat()
        return ProjectDocumentFileRecord(
            path=document_path,
            content=content,
            updated_at=datetime.fromtimestamp(stats.st_mtime, tz=UTC),
        )

    def _resolve_project_document_path(
        self,
        project_id: uuid.UUID,
        document_path: str,
    ) -> Path:
        normalized = self._normalize_document_path(document_path)
        return self.root / "projects" / str(project_id) / "documents" / normalized

    def _normalize_document_path(self, document_path: str) -> Path:
        normalized = document_path.strip()
        if not normalized:
            raise BusinessRuleError("文稿路径不能为空")
        pure_path = PurePosixPath(normalized)
        if pure_path.is_absolute() or not pure_path.parts:
            raise BusinessRuleError("文稿路径必须是项目内相对路径")
        invalid_parts = {".", "..", ""}
        if any(part in invalid_parts for part in pure_path.parts):
            raise BusinessRuleError("文稿路径不能包含非法目录跳转")
        if pure_path.suffix.lower() != ".md":
            raise BusinessRuleError("当前仅支持保存 Markdown 文稿文件")
        return Path(*pure_path.parts)
