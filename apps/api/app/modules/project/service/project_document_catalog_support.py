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

from .project_document_version_support import normalize_project_file_document_content

from .project_document_capability_dto import (
    ProjectDocumentCatalogEntryDTO,
    ProjectDocumentContentState,
    ProjectDocumentReadErrorDTO,
    ProjectDocumentReadItemDTO,
)
from .project_document_support import (
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH,
    CHARACTERS_DATA_DOCUMENT_PATH,
    DATA_SCHEMA_DOCUMENT_PATH,
    EVENTS_DATA_DOCUMENT_PATH,
    FACTION_RELATIONS_DATA_DOCUMENT_PATH,
    FACTIONS_DATA_DOCUMENT_PATH,
    MEMBERSHIPS_DATA_DOCUMENT_PATH,
)

if TYPE_CHECKING:
    from app.modules.project.infrastructure import ProjectDocumentTreeNodeRecord

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


@dataclass(frozen=True)
class ResolvedProjectDocumentCatalogRecord:
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


def _flatten_tree_file_paths(nodes: list[ProjectDocumentTreeNodeRecord]) -> list[str]:
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


def _resolve_catalog_content_state(
    *,
    version_number: int | None,
    word_count: int | None,
) -> ProjectDocumentContentState:
    if version_number is None:
        return "empty"
    if (word_count or 0) > 0:
        return "ready"
    return "empty"


def _resolve_visible_content_state(
    document: ResolvedProjectDocument | ResolvedProjectDocumentCatalogRecord,
) -> ProjectDocumentContentState:
    if not document.readable:
        return "placeholder"
    return document.content_state


def _pair_paths_and_cursors(paths: list[str], cursors: list[str]) -> tuple[str | None, ...]:
    if not cursors:
        return tuple(None for _ in paths)
    if len(paths) != len(cursors):
        raise ValueError("cursors must align with paths")
    return tuple(cursor or None for cursor in cursors)


def _build_catalog_version(
    documents: Iterable[ResolvedProjectDocument | ResolvedProjectDocumentCatalogRecord],
) -> str:
    items = sorted(documents, key=lambda item: item.path)
    payload = json.dumps(
        [
            {
                "document_ref": item.document_ref,
                "document_kind": item.document_kind,
                "content_state": item.content_state,
                "mime_type": item.mime_type,
                "path": item.path,
                "resource_uri": item.resource_uri,
                "schema_id": item.schema_id,
                "source": item.source,
                "title": item.title,
                "version": item.version,
                "writable": item.writable,
            }
            for item in items
        ],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"catalog:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _build_resource_uri(project_id: uuid.UUID, document_ref: str) -> str:
    return f"{PROJECT_DOCUMENT_RESOURCE_SCHEME}://{project_id}/{quote(document_ref, safe='')}"


def _build_content_hash(content: str) -> str:
    normalized_content = normalize_project_file_document_content(content)
    return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()


def _build_binding_version(
    document: ResolvedProjectDocument | ResolvedProjectDocumentCatalogRecord,
) -> str:
    payload = json.dumps(
        _build_binding_version_payload(document),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_binding_version_payload(
    document: ResolvedProjectDocument | ResolvedProjectDocumentCatalogRecord,
) -> dict[str, object]:
    return {
        "document_ref": document.document_ref,
        "document_kind": document.document_kind,
        "path": document.path,
        "source": document.source,
        "writable": document.writable,
    }


def _to_catalog_entry(
    document: ResolvedProjectDocument | ResolvedProjectDocumentCatalogRecord,
    *,
    catalog_version: str,
) -> ProjectDocumentCatalogEntryDTO:
    return ProjectDocumentCatalogEntryDTO(
        path=document.path,
        document_ref=document.document_ref,
        binding_version=_build_binding_version(document),
        resource_uri=document.resource_uri,
        title=document.title,
        source=document.source,
        document_kind=document.document_kind,
        mime_type=document.mime_type,
        schema_id=document.schema_id,
        content_state=_resolve_visible_content_state(document),
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
        code = str(exc)
        return None, ProjectDocumentReadErrorDTO(
            path=document.path,
            code=code,
            message=_build_read_error_message(code),
        )
    return ProjectDocumentReadItemDTO(
        path=document.path,
        document_ref=document.document_ref,
        binding_version=_build_binding_version(document),
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
