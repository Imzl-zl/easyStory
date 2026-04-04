from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import quote
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content

from .project_document_capability_dto import (
    ProjectDocumentCatalogEntryDTO,
    ProjectDocumentContentState,
    ProjectDocumentReadErrorDTO,
    ProjectDocumentReadItemDTO,
    ProjectDocumentReadResultDTO,
)
from .project_document_support import (
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH,
    CHARACTERS_DATA_DOCUMENT_PATH,
    DATA_SCHEMA_DOCUMENT_PATH,
    EVENTS_DATA_DOCUMENT_PATH,
    FACTION_RELATIONS_DATA_DOCUMENT_PATH,
    FACTIONS_DATA_DOCUMENT_PATH,
    MEMBERSHIPS_DATA_DOCUMENT_PATH,
    OPENING_PLAN_DOCUMENT_PATH,
    OUTLINE_DOCUMENT_PATH,
    is_mutable_project_document_file_path,
    parse_chapter_number_from_document_path,
)
from .project_service import ProjectService
from .project_service_support import current_version

if TYPE_CHECKING:
    from app.modules.project.infrastructure import (
        ProjectDocumentFileStore,
        ProjectDocumentIdentityStore,
        ProjectDocumentTreeNodeRecord,
    )

PROJECT_DOCUMENT_RESOURCE_SCHEME = "project-document"
DEFAULT_CHAPTER_PATH_TEMPLATE = "正文/第{chapter_number:03d}章.md"
JSON_MIME_TYPE = "application/json"
MARKDOWN_MIME_TYPE = "text/markdown"
PROJECT_DOCUMENT_READ_WINDOW_CHARS = 4000
PROJECT_DOCUMENT_READ_CURSOR_PREFIX = "offset:"
PROJECT_DOCUMENT_MIN_MEANINGFUL_CHARS = 256
PROJECT_DOCUMENT_SCHEMA_IDS = {
    DATA_SCHEMA_DOCUMENT_PATH: "project.data_schema",
    CHARACTERS_DATA_DOCUMENT_PATH: "project.characters",
    FACTIONS_DATA_DOCUMENT_PATH: "project.factions",
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH: "project.character_relations",
    FACTION_RELATIONS_DATA_DOCUMENT_PATH: "project.faction_relations",
    MEMBERSHIPS_DATA_DOCUMENT_PATH: "project.memberships",
    EVENTS_DATA_DOCUMENT_PATH: "project.events",
}


@dataclass(frozen=True)
class ResolvedProjectDocument:
    content: str
    content_state: ProjectDocumentContentState
    document_kind: str
    document_ref: str
    mime_type: str
    path: str
    resource_uri: str
    schema_id: str | None
    source: str
    title: str
    updated_at: datetime | None
    version: str
    writable: bool
    readable: bool


class ProjectDocumentCapabilityService:
    def __init__(
        self,
        *,
        project_service: ProjectService,
        document_file_store: "ProjectDocumentFileStore | None" = None,
        document_identity_store: "ProjectDocumentIdentityStore | None" = None,
    ) -> None:
        self.project_service = project_service
        self.document_file_store = document_file_store or project_service.document_file_store
        self.document_identity_store = document_identity_store

    async def list_document_catalog(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[ProjectDocumentCatalogEntryDTO]:
        documents = await self._resolve_documents(db, project_id, owner_id=owner_id)
        catalog_version = _build_catalog_version(documents.values())
        return [
            _to_catalog_entry(document, catalog_version=catalog_version)
            for document in documents.values()
        ]

    async def read_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        paths: Iterable[str],
        cursors: Iterable[str] | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentReadResultDTO:
        requested_paths = list(paths)
        requested_cursors = list(cursors or [])
        documents = await self._resolve_documents(db, project_id, owner_id=owner_id)
        catalog_version = _build_catalog_version(documents.values())
        items: list[ProjectDocumentReadItemDTO] = []
        errors: list[ProjectDocumentReadErrorDTO] = []
        cursor_by_path = _pair_paths_and_cursors(requested_paths, requested_cursors)
        for path in requested_paths:
            resolved = documents.get(path)
            if resolved is None:
                errors.append(
                    ProjectDocumentReadErrorDTO(
                        path=path,
                        code="document_not_found",
                        message="目标文稿不存在于当前项目目录",
                    )
                )
                continue
            cursor = cursor_by_path.get(path)
            read_item, read_error = _build_read_projection(
                resolved,
                catalog_version=catalog_version,
                cursor=cursor,
            )
            if read_error is not None:
                errors.append(read_error)
                continue
            items.append(read_item)
        return ProjectDocumentReadResultDTO(
            documents=items,
            errors=errors,
            catalog_version=catalog_version,
        )

    async def _resolve_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> dict[str, ResolvedProjectDocument]:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        contents = await self._load_project_contents(db, project.id)
        chapter_paths, file_paths = self._collect_file_layer_paths(project.id)
        resolved_documents = self._build_file_documents(project.id, file_paths)
        resolved_documents.update(self._build_canonical_documents(project.id, contents, chapter_paths))
        return dict(sorted(resolved_documents.items(), key=lambda item: item[0]))

    async def _load_project_contents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> list[Content]:
        return (
            await db.scalars(
                select(Content)
                .options(selectinload(Content.versions))
                .where(Content.project_id == project_id)
            )
        ).all()

    def _collect_file_layer_paths(
        self,
        project_id: uuid.UUID,
    ) -> tuple[dict[int, str], list[str]]:
        if self.document_file_store is None:
            return {}, []
        chapter_paths: dict[int, str] = {}
        file_paths: list[str] = []
        for path in _flatten_tree_file_paths(self.document_file_store.list_project_document_tree(project_id)):
            if path in {OUTLINE_DOCUMENT_PATH, OPENING_PLAN_DOCUMENT_PATH}:
                continue
            chapter_number = parse_chapter_number_from_document_path(path)
            if chapter_number is not None:
                chapter_paths[chapter_number] = path
                continue
            file_paths.append(path)
        return chapter_paths, file_paths

    def _build_file_documents(
        self,
        project_id: uuid.UUID,
        file_paths: list[str],
    ) -> dict[str, ResolvedProjectDocument]:
        if self.document_file_store is None:
            return {}
        documents: dict[str, ResolvedProjectDocument] = {}
        for path in sorted(file_paths):
            record = self.document_file_store.find_project_document(project_id, path)
            if record is None:
                continue
            document_ref = self._resolve_file_document_ref(project_id, path=path)
            documents[path] = ResolvedProjectDocument(
                content=record.content,
                content_state=_resolve_content_state(record.content),
                document_kind=_resolve_document_kind(path, source="file"),
                document_ref=document_ref,
                mime_type=_resolve_mime_type(path),
                path=path,
                resource_uri=_build_resource_uri(project_id, document_ref),
                schema_id=PROJECT_DOCUMENT_SCHEMA_IDS.get(path),
                source="file",
                title=_resolve_title(path),
                updated_at=record.updated_at,
                version=_build_content_hash_version(record.content),
                writable=is_mutable_project_document_file_path(path),
                readable=True,
            )
        return documents

    def _build_canonical_documents(
        self,
        project_id: uuid.UUID,
        contents: list[Content],
        chapter_paths: dict[int, str],
    ) -> dict[str, ResolvedProjectDocument]:
        content_by_type = {item.content_type: item for item in contents if item.content_type in {"outline", "opening_plan"}}
        chapter_contents = sorted(
            (item for item in contents if item.content_type == "chapter" and item.chapter_number is not None),
            key=lambda item: item.chapter_number or 0,
        )
        resolved = {
            OUTLINE_DOCUMENT_PATH: self._build_canonical_document(
                project_id,
                path=OUTLINE_DOCUMENT_PATH,
                content=content_by_type.get("outline"),
                document_ref="canonical:outline",
                source="outline",
            ),
            OPENING_PLAN_DOCUMENT_PATH: self._build_canonical_document(
                project_id,
                path=OPENING_PLAN_DOCUMENT_PATH,
                content=content_by_type.get("opening_plan"),
                document_ref="canonical:opening_plan",
                source="opening_plan",
            ),
        }
        for item in chapter_contents:
            chapter_number = item.chapter_number
            if chapter_number is None:
                continue
            path = chapter_paths.get(chapter_number, DEFAULT_CHAPTER_PATH_TEMPLATE.format(chapter_number=chapter_number))
            resolved[path] = self._build_canonical_document(
                project_id,
                path=path,
                content=item,
                document_ref=f"canonical:chapter:{chapter_number:03d}",
                source="chapter",
            )
        return resolved

    def _build_canonical_document(
        self,
        project_id: uuid.UUID,
        *,
        path: str,
        content: Content | None,
        document_ref: str,
        source: str,
    ) -> ResolvedProjectDocument:
        version = current_version(content) if content is not None else None
        content_text = version.content_text if version is not None else ""
        updated_at = content.last_edited_at if content is not None else None
        if updated_at is None and version is not None:
            updated_at = version.created_at
        return ResolvedProjectDocument(
            content=content_text,
            content_state=_resolve_content_state(content_text),
            document_kind=content.content_type if content is not None else source,
            document_ref=document_ref,
            mime_type=MARKDOWN_MIME_TYPE,
            path=path,
            resource_uri=_build_resource_uri(project_id, document_ref),
            schema_id=None,
            source=source,
            title=content.title if content is not None else _resolve_title(path),
            updated_at=updated_at,
            version=_build_canonical_version(document_ref, version_id=version.id if version is not None else None),
            writable=False,
            readable=content is not None and version is not None,
        )

    def _resolve_file_document_ref(
        self,
        project_id: uuid.UUID,
        *,
        path: str,
    ) -> str:
        if self.document_identity_store is None:
            return f"project_file:{path}"
        return self.document_identity_store.resolve_document_ref(project_id, path=path)


def _flatten_tree_file_paths(nodes: list["ProjectDocumentTreeNodeRecord"]) -> list[str]:
    paths: list[str] = []
    for node in nodes:
        if node.node_type == "file":
            paths.append(node.path)
            continue
        paths.extend(_flatten_tree_file_paths(list(node.children)))
    return paths


def _resolve_title(path: str) -> str:
    return PurePosixPath(path).name


def _resolve_document_kind(path: str, *, source: str) -> str:
    if source != "file":
        return source
    if path.endswith(".json"):
        return "json"
    return "markdown"


def _resolve_mime_type(path: str) -> str:
    if path.endswith(".json"):
        return JSON_MIME_TYPE
    return MARKDOWN_MIME_TYPE


def _resolve_content_state(content: str) -> ProjectDocumentContentState:
    if content:
        return "ready"
    return "empty"


def _pair_paths_and_cursors(paths: list[str], cursors: list[str]) -> dict[str, str]:
    if not cursors:
        return {}
    if len(paths) != len(cursors):
        raise ValueError("cursors must align with paths")
    return {
        path: cursor
        for path, cursor in zip(paths, cursors, strict=True)
        if cursor
    }


def _build_catalog_version(documents: Iterable[ResolvedProjectDocument]) -> str:
    payload = json.dumps(
        [
            {
                "document_ref": item.document_ref,
                "path": item.path,
                "source": item.source,
                "writable": item.writable,
            }
            for item in documents
        ],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"catalog:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _build_resource_uri(project_id: uuid.UUID, document_ref: str) -> str:
    return f"{PROJECT_DOCUMENT_RESOURCE_SCHEME}://{project_id}/{quote(document_ref, safe='')}"


def _build_content_hash_version(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def _build_canonical_version(document_ref: str, *, version_id: uuid.UUID | None) -> str:
    if version_id is not None:
        return f"{document_ref}:version:{version_id}"
    return f"{document_ref}:empty"


def _to_catalog_entry(
    document: ResolvedProjectDocument,
    *,
    catalog_version: str,
) -> ProjectDocumentCatalogEntryDTO:
    return ProjectDocumentCatalogEntryDTO(
        path=document.path,
        document_ref=document.document_ref,
        resource_uri=document.resource_uri,
        title=document.title,
        source=document.source,
        document_kind=document.document_kind,
        mime_type=document.mime_type,
        schema_id=document.schema_id,
        content_state="placeholder" if not document.readable else document.content_state,
        writable=document.writable,
        version=document.version,
        updated_at=document.updated_at,
        catalog_version=catalog_version,
    )


def _build_read_projection(
    document: ResolvedProjectDocument,
    *,
    catalog_version: str,
    cursor: str | None,
) -> tuple[ProjectDocumentReadItemDTO | None, ProjectDocumentReadErrorDTO | None]:
    if not document.readable:
        return None, ProjectDocumentReadErrorDTO(
            path=document.path,
            code="document_not_readable",
            message="目标文稿当前尚未物化，暂时不可读取",
        )
    try:
        content, truncated, next_cursor = _slice_document_content(document.content, cursor=cursor)
    except ValueError as exc:
        return None, ProjectDocumentReadErrorDTO(
            path=document.path,
            code=str(exc),
            message=_build_read_error_message(str(exc)),
        )
    return ProjectDocumentReadItemDTO(
        path=document.path,
        document_ref=document.document_ref,
        resource_uri=document.resource_uri,
        title=document.title,
        source=document.source,
        document_kind=document.document_kind,
        mime_type=document.mime_type,
        schema_id=document.schema_id,
        content_state=document.content_state,
        writable=document.writable,
        version=document.version,
        updated_at=document.updated_at,
        catalog_version=catalog_version,
        content=content,
        truncated=truncated,
        next_cursor=next_cursor,
    ), None


def _slice_document_content(
    content: str,
    *,
    cursor: str | None,
) -> tuple[str, bool, str | None]:
    offset = _parse_cursor(cursor)
    if len(content) <= PROJECT_DOCUMENT_READ_WINDOW_CHARS:
        return content, False, None
    if PROJECT_DOCUMENT_READ_WINDOW_CHARS < PROJECT_DOCUMENT_MIN_MEANINGFUL_CHARS:
        raise ValueError("content_too_large")
    if offset >= len(content):
        raise ValueError("invalid_cursor")
    next_offset = min(offset + PROJECT_DOCUMENT_READ_WINDOW_CHARS, len(content))
    next_cursor = None
    if next_offset < len(content):
        next_cursor = f"{PROJECT_DOCUMENT_READ_CURSOR_PREFIX}{next_offset}"
    return content[offset:next_offset], next_cursor is not None, next_cursor


def _parse_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    if not cursor.startswith(PROJECT_DOCUMENT_READ_CURSOR_PREFIX):
        raise ValueError("invalid_cursor")
    raw_offset = cursor.removeprefix(PROJECT_DOCUMENT_READ_CURSOR_PREFIX)
    if not raw_offset.isdigit():
        raise ValueError("invalid_cursor")
    return int(raw_offset)


def _build_read_error_message(code: str) -> str:
    if code == "invalid_cursor":
        return "读取锚点无效，无法继续读取该文稿"
    if code == "content_too_large":
        return "当前读取窗口不足以返回有意义的内容片段"
    return "读取文稿失败"
