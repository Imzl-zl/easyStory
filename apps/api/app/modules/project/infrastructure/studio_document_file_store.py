from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import shutil
import uuid
from contextlib import contextmanager
from typing import Literal

from app.shared.runtime.errors import BusinessRuleError

from .file_atomic_support import exclusive_file_lock, write_text_atomically

ProjectDocumentEntryType = Literal["file", "folder"]
PROJECT_DOCUMENT_TEMPLATE_MARKER_PREFIX = ".studio-template-v"
PROJECT_DOCUMENT_TREE_LOCK_FILE = ".document_tree.lock"
PROJECT_DOCUMENT_DELETE_STAGING_DIR = ".delete-staging"
SUPPORTED_PROJECT_DOCUMENT_FILE_SUFFIXES = {".json", ".md"}
FILE_HASH_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class ProjectDocumentFileRecord:
    path: str
    content: str
    updated_at: datetime


@dataclass(frozen=True)
class ProjectDocumentFileMetadataRecord:
    content_hash: str
    path: str
    size_bytes: int
    updated_at: datetime


@dataclass(frozen=True)
class ProjectDocumentEntryRecord:
    label: str
    node_type: ProjectDocumentEntryType
    path: str


@dataclass(frozen=True)
class ProjectDocumentStagedDeleteRecord:
    entry: ProjectDocumentEntryRecord
    staged_path: Path


@dataclass(frozen=True)
class ProjectDocumentTreeNodeRecord:
    children: tuple["ProjectDocumentTreeNodeRecord", ...] = ()
    label: str = ""
    node_type: ProjectDocumentEntryType = "folder"
    path: str = ""


class ProjectDocumentFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    @contextmanager
    def project_document_tree_lock(self, project_id: uuid.UUID):
        with exclusive_file_lock(self._resolve_project_tree_lock_path(project_id)):
            yield

    def bootstrap_project_document_template(
        self,
        project_id: uuid.UUID,
        *,
        folder_paths: tuple[str, ...],
        file_entries: tuple[tuple[str, str], ...],
        template_version: int,
    ) -> None:
        if self.get_project_document_template_version(project_id) >= template_version:
            return
        for folder_path in folder_paths:
            self._ensure_template_folder(project_id, folder_path)
        for document_path, content in file_entries:
            self._ensure_template_file(project_id, document_path, content)
        self._write_template_marker(project_id, template_version)

    def backfill_project_document_template(
        self,
        project_id: uuid.UUID,
        *,
        folder_paths: tuple[str, ...],
        file_entries: tuple[tuple[str, str], ...],
        template_version: int,
    ) -> None:
        if self.get_project_document_template_version(project_id) >= template_version:
            return
        for folder_path in folder_paths:
            self._ensure_template_folder(project_id, folder_path)
        for document_path, content in file_entries:
            self._ensure_template_file(project_id, document_path, content)
        self._write_template_marker(project_id, template_version)

    def find_project_document(
        self,
        project_id: uuid.UUID,
        document_path: str,
    ) -> ProjectDocumentFileRecord | None:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_project_document_path(project_id, document_path)
        if not resolved.exists():
            return None
        stats = resolved.stat()
        return ProjectDocumentFileRecord(
            path=self._read_relative_entry_path(project_root, resolved),
            content=resolved.read_text(encoding="utf-8"),
            updated_at=datetime.fromtimestamp(stats.st_mtime, tz=UTC),
        )

    def find_project_document_metadata(
        self,
        project_id: uuid.UUID,
        document_path: str,
    ) -> ProjectDocumentFileMetadataRecord | None:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_project_document_path(project_id, document_path)
        if not resolved.exists():
            return None
        stats = resolved.stat()
        return ProjectDocumentFileMetadataRecord(
            content_hash=_build_file_content_hash(resolved),
            path=self._read_relative_entry_path(project_root, resolved),
            size_bytes=stats.st_size,
            updated_at=datetime.fromtimestamp(stats.st_mtime, tz=UTC),
        )

    def save_project_document(
        self,
        project_id: uuid.UUID,
        document_path: str,
        content: str,
        *,
        expected_version: str | None = None,
    ) -> ProjectDocumentFileRecord:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_project_document_path(project_id, document_path)
        self._ensure_parent_directory_ready(project_root, resolved.parent)
        if expected_version is not None:
            from app.modules.project.service.project_document_version_support import (
                build_project_file_document_version,
            )

            current_content = resolved.read_text(encoding="utf-8") if resolved.exists() else ""
            current_version = build_project_file_document_version(current_content)
            if current_version != expected_version:
                raise BusinessRuleError("目标文稿版本已变化，请重新读取最新内容后再写入。")
        write_text_atomically(resolved, content)
        stats = resolved.stat()
        return ProjectDocumentFileRecord(
            path=self._read_relative_entry_path(project_root, resolved),
            content=content,
            updated_at=datetime.fromtimestamp(stats.st_mtime, tz=UTC),
        )

    def list_project_document_tree(self, project_id: uuid.UUID) -> list[ProjectDocumentTreeNodeRecord]:
        project_root = self._resolve_project_document_root(project_id)
        if not project_root.exists():
            return []
        nodes = [self._build_tree_node(project_root, child) for child in self._iter_sorted_entries(project_root)]
        return [node for node in nodes if node is not None]

    def find_project_document_entry(
        self,
        project_id: uuid.UUID,
        entry_path: str,
    ) -> ProjectDocumentEntryRecord | None:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_existing_project_entry_path(project_id, entry_path)
        if resolved is None:
            return None
        return self._build_entry_record(project_root, resolved)

    def create_project_document_file(
        self,
        project_id: uuid.UUID,
        document_path: str,
    ) -> ProjectDocumentEntryRecord:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_project_document_path(project_id, document_path)
        self._ensure_path_is_available(resolved, "文稿")
        self._ensure_parent_directory_ready(project_root, resolved.parent)
        resolved.write_text("", encoding="utf-8")
        return self._build_entry_record(project_root, resolved)

    def create_project_document_folder(
        self,
        project_id: uuid.UUID,
        folder_path: str,
    ) -> ProjectDocumentEntryRecord:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_project_folder_path(project_id, folder_path)
        self._ensure_path_is_available(resolved, "目录")
        self._ensure_parent_directory_ready(project_root, resolved.parent)
        resolved.mkdir()
        return self._build_entry_record(project_root, resolved)

    def rename_project_document_entry(
        self,
        project_id: uuid.UUID,
        source_path: str,
        node_type: ProjectDocumentEntryType,
        next_path: str,
    ) -> ProjectDocumentEntryRecord:
        project_root = self._resolve_project_document_root(project_id)
        source = self._resolve_existing_project_entry_path(project_id, source_path)
        if source is None:
            raise BusinessRuleError("目标文稿不存在")
        target = (
            self._resolve_project_document_path(project_id, next_path)
            if node_type == "file"
            else self._resolve_project_folder_path(project_id, next_path)
        )
        self._ensure_path_is_available(target, "目标路径")
        self._ensure_parent_directory_ready(project_root, target.parent)
        source.rename(target)
        return self._build_entry_record(project_root, target)

    def delete_project_document_entry(
        self,
        project_id: uuid.UUID,
        entry_path: str,
    ) -> ProjectDocumentEntryRecord:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_existing_project_entry_path(project_id, entry_path)
        if resolved is None:
            raise BusinessRuleError("目标文稿不存在")
        record = self._build_entry_record(project_root, resolved)
        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink()
        return record

    def stage_project_document_entry_delete(
        self,
        project_id: uuid.UUID,
        entry_path: str,
    ) -> ProjectDocumentStagedDeleteRecord:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_existing_project_entry_path(project_id, entry_path)
        if resolved is None:
            raise BusinessRuleError("目标文稿不存在")
        record = self._build_entry_record(project_root, resolved)
        staging_path = self._resolve_delete_staging_root(project_id) / str(uuid.uuid4()) / resolved.name
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        resolved.rename(staging_path)
        return ProjectDocumentStagedDeleteRecord(entry=record, staged_path=staging_path)

    def restore_staged_project_document_entry(
        self,
        project_id: uuid.UUID,
        staged: ProjectDocumentStagedDeleteRecord,
    ) -> ProjectDocumentEntryRecord:
        project_root = self._resolve_project_document_root(project_id)
        target_path = project_root / Path(*PurePosixPath(staged.entry.path).parts)
        self._ensure_parent_directory_ready(project_root, target_path.parent)
        self._ensure_path_is_available(target_path, "恢复路径")
        staged.staged_path.rename(target_path)
        self._cleanup_delete_staging_dirs(project_id, staged.staged_path)
        return self._build_entry_record(project_root, target_path)

    def finalize_staged_project_document_entry_delete(
        self,
        project_id: uuid.UUID,
        staged: ProjectDocumentStagedDeleteRecord,
    ) -> None:
        if staged.staged_path.is_dir():
            shutil.rmtree(staged.staged_path)
        elif staged.staged_path.exists():
            staged.staged_path.unlink()
        self._cleanup_delete_staging_dirs(project_id, staged.staged_path)

    def _build_tree_node(
        self,
        project_root: Path,
        current_path: Path,
    ) -> ProjectDocumentTreeNodeRecord | None:
        relative_path = current_path.relative_to(project_root).as_posix()
        if current_path.is_dir():
            children = tuple(
                child
                for child in (
                    self._build_tree_node(project_root, item)
                    for item in self._iter_sorted_entries(current_path)
                )
                if child is not None
            )
            return ProjectDocumentTreeNodeRecord(
                children=children,
                label=current_path.name,
                node_type="folder",
                path=relative_path,
            )
        if current_path.suffix.lower() not in SUPPORTED_PROJECT_DOCUMENT_FILE_SUFFIXES:
            return None
        return ProjectDocumentTreeNodeRecord(
            children=(),
            label=current_path.name,
            node_type="file",
            path=relative_path,
        )

    def _resolve_project_document_path(
        self,
        project_id: uuid.UUID,
        document_path: str,
    ) -> Path:
        normalized = self._normalize_file_path(document_path)
        return self._resolve_project_document_root(project_id) / normalized

    def _resolve_project_folder_path(
        self,
        project_id: uuid.UUID,
        folder_path: str,
    ) -> Path:
        normalized = self._normalize_folder_path(folder_path)
        return self._resolve_project_document_root(project_id) / normalized

    def _resolve_existing_project_entry_path(
        self,
        project_id: uuid.UUID,
        entry_path: str,
    ) -> Path | None:
        normalized = self._normalize_relative_path(entry_path)
        resolved = self._resolve_project_document_root(project_id) / normalized
        return resolved if resolved.exists() else None

    def _resolve_project_document_root(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / "documents"

    def _resolve_project_tree_lock_path(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / PROJECT_DOCUMENT_TREE_LOCK_FILE

    def _resolve_delete_staging_root(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / PROJECT_DOCUMENT_DELETE_STAGING_DIR

    def get_project_document_template_version(self, project_id: uuid.UUID) -> int:
        project_root = self._resolve_project_document_root(project_id)
        if not project_root.exists():
            return 0
        versions = [
            version
            for version in (
                self._parse_template_marker_version(entry.name)
                for entry in project_root.iterdir()
                if entry.is_file()
            )
            if version is not None
        ]
        return max(versions, default=0)

    def _build_entry_record(
        self,
        project_root: Path,
        resolved: Path,
    ) -> ProjectDocumentEntryRecord:
        return ProjectDocumentEntryRecord(
            label=resolved.name,
            node_type="folder" if resolved.is_dir() else "file",
            path=self._read_relative_entry_path(project_root, resolved),
        )

    def _normalize_file_path(self, document_path: str) -> Path:
        pure_path = self._normalize_relative_path(document_path)
        if pure_path.suffix.lower() not in SUPPORTED_PROJECT_DOCUMENT_FILE_SUFFIXES:
            raise BusinessRuleError("当前仅支持保存 .md 或 .json 文稿文件")
        return Path(*pure_path.parts)

    def _normalize_folder_path(self, folder_path: str) -> Path:
        pure_path = self._normalize_relative_path(folder_path)
        if pure_path.suffix.lower() in SUPPORTED_PROJECT_DOCUMENT_FILE_SUFFIXES:
            raise BusinessRuleError("目录名称不能以 .md 或 .json 结尾")
        return Path(*pure_path.parts)

    def _normalize_relative_path(self, path_value: str) -> PurePosixPath:
        normalized = path_value.strip()
        if not normalized:
            raise BusinessRuleError("文稿路径不能为空")
        pure_path = PurePosixPath(normalized)
        if pure_path.is_absolute() or not pure_path.parts:
            raise BusinessRuleError("文稿路径必须是项目内相对路径")
        invalid_parts = {".", "..", ""}
        if any(part in invalid_parts for part in pure_path.parts):
            raise BusinessRuleError("文稿路径不能包含非法目录跳转")
        return pure_path

    def _ensure_parent_directory_ready(self, project_root: Path, parent_path: Path) -> None:
        relative_parent = parent_path.relative_to(project_root)
        if len(relative_parent.parts) <= 1:
            parent_path.mkdir(parents=True, exist_ok=True)
            return
        if not parent_path.exists():
            raise BusinessRuleError("上级目录不存在，请先创建目录")
        if not parent_path.is_dir():
            raise BusinessRuleError("上级路径不是目录")

    def _ensure_path_is_available(self, path: Path, label: str) -> None:
        if path.exists():
            raise BusinessRuleError(f"{label}已存在")

    def _iter_sorted_entries(self, path: Path) -> list[Path]:
        return sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower(), item.name))

    def _read_relative_entry_path(self, project_root: Path, resolved: Path) -> str:
        return resolved.relative_to(project_root).as_posix()

    def _ensure_template_file(
        self,
        project_id: uuid.UUID,
        document_path: str,
        content: str,
    ) -> None:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_project_document_path(project_id, document_path)
        self._ensure_template_parent_directory(project_root, resolved.parent)
        if resolved.exists():
            if resolved.is_dir():
                raise BusinessRuleError("模板文稿路径与现有目录冲突")
            return
        resolved.write_text(content, encoding="utf-8")

    def _ensure_template_folder(
        self,
        project_id: uuid.UUID,
        folder_path: str,
    ) -> None:
        project_root = self._resolve_project_document_root(project_id)
        resolved = self._resolve_project_folder_path(project_id, folder_path)
        self._ensure_template_parent_directory(project_root, resolved.parent)
        if resolved.exists():
            if not resolved.is_dir():
                raise BusinessRuleError("模板目录路径与现有文稿冲突")
            return
        resolved.mkdir()

    def _ensure_template_parent_directory(self, project_root: Path, parent_path: Path) -> None:
        parent_path.mkdir(parents=True, exist_ok=True)
        if not parent_path.is_dir():
            raise BusinessRuleError("模板上级路径不是目录")
        project_root.mkdir(parents=True, exist_ok=True)

    def _write_template_marker(self, project_id: uuid.UUID, template_version: int) -> None:
        marker_path = self._resolve_template_marker_path(project_id, template_version)
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_atomically(marker_path, marker_path.name)
        self._cleanup_stale_template_markers(marker_path.parent, keep_name=marker_path.name)

    def _resolve_template_marker_path(self, project_id: uuid.UUID, template_version: int) -> Path:
        return self._resolve_project_document_root(project_id) / (
            f"{PROJECT_DOCUMENT_TEMPLATE_MARKER_PREFIX}{template_version}"
        )

    def _cleanup_stale_template_markers(self, project_root: Path, *, keep_name: str) -> None:
        for entry in project_root.iterdir():
            if entry.is_file() and entry.name.startswith(PROJECT_DOCUMENT_TEMPLATE_MARKER_PREFIX) and entry.name != keep_name:
                entry.unlink()

    def _cleanup_delete_staging_dirs(self, project_id: uuid.UUID, staged_path: Path) -> None:
        staging_root = self._resolve_delete_staging_root(project_id)
        current = staged_path.parent
        while current != staging_root:
            if current.exists() and any(current.iterdir()):
                return
            if current.exists():
                current.rmdir()
            current = current.parent
        if staging_root.exists() and not any(staging_root.iterdir()):
            staging_root.rmdir()

    def _parse_template_marker_version(self, filename: str) -> int | None:
        if not filename.startswith(PROJECT_DOCUMENT_TEMPLATE_MARKER_PREFIX):
            return None
        suffix = filename.removeprefix(PROJECT_DOCUMENT_TEMPLATE_MARKER_PREFIX)
        return int(suffix) if suffix.isdigit() else None


def _build_file_content_hash(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(FILE_HASH_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
