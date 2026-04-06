from __future__ import annotations

from datetime import datetime, timezone

from app.modules.content.models import Content, ContentVersion
from app.modules.project.service.project_document_version_support import (
    build_project_canonical_document_version,
)
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import (
    ChapterDetailDTO,
    ChapterImpactSummaryDTO,
    ChapterSaveDTO,
    ChapterSummaryDTO,
    ChapterVersionDTO,
)

CHAPTER_TYPE = "chapter"
PREPARATION_ASSET_TYPES = ("outline", "opening_plan")


def count_text_units(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def sorted_versions(content: Content) -> list[ContentVersion]:
    return sorted(content.versions, key=lambda item: item.version_number, reverse=True)


def require_current_version(content: Content) -> ContentVersion:
    for version in sorted_versions(content):
        if version.is_current:
            return version
    raise BusinessRuleError(f"第{content.chapter_number}章缺少当前版本")


def require_version(content: Content, version_number: int) -> ContentVersion:
    for version in content.versions:
        if version.version_number == version_number:
            return version
    raise NotFoundError(
        f"Chapter version not found: chapter={content.chapter_number}, version={version_number}"
    )


def next_version_number(content: Content) -> int:
    if not content.versions:
        return 1
    return max(version.version_number for version in content.versions) + 1


def clear_current_version(content: Content) -> None:
    for version in content.versions:
        if version.is_current:
            version.is_current = False


def append_chapter_version(content: Content, payload: ChapterSaveDTO) -> None:
    clear_current_version(content)
    content.title = payload.title
    content.status = "draft"
    content.last_edited_at = datetime.now(timezone.utc)
    content.versions.append(
        ContentVersion(
            content_id=content.id,
            version_number=next_version_number(content),
            content_text=payload.content_text,
            created_by=payload.created_by,
            change_source=payload.change_source,
            change_summary=payload.change_summary,
            is_current=True,
            is_best=False,
            word_count=count_text_units(payload.content_text),
            context_snapshot_hash=payload.context_snapshot_hash,
        )
    )


def build_rollback_payload(
    content: Content,
    source_version: ContentVersion,
) -> ChapterSaveDTO:
    return ChapterSaveDTO(
        title=content.title,
        content_text=source_version.content_text,
        change_summary=f"回滚至版本 v{source_version.version_number}",
        created_by="user",
        change_source="user_edit",
        context_snapshot_hash=source_version.context_snapshot_hash,
    )


def best_version_number(content: Content) -> int | None:
    for version in sorted_versions(content):
        if version.is_best:
            return version.version_number
    return None


def to_summary(content: Content) -> ChapterSummaryDTO:
    version = require_current_version(content)
    return ChapterSummaryDTO(
        project_id=content.project_id,
        content_id=content.id,
        chapter_number=content.chapter_number or 0,
        title=content.title,
        status=content.status,
        current_version_number=version.version_number,
        document_version=build_project_canonical_document_version(
            f"canonical:chapter:{(content.chapter_number or 0):03d}",
            content_id=content.id,
            version_number=version.version_number,
        ),
        best_version_number=best_version_number(content),
        word_count=version.word_count,
        last_edited_at=content.last_edited_at,
    )


def to_detail(
    content: Content,
    *,
    impact: ChapterImpactSummaryDTO | None = None,
) -> ChapterDetailDTO:
    version = require_current_version(content)
    summary = to_summary(content)
    return ChapterDetailDTO(
        **summary.model_dump(),
        content_text=version.content_text,
        change_summary=version.change_summary,
        created_by=version.created_by,
        change_source=version.change_source,
        context_snapshot_hash=version.context_snapshot_hash,
        impact=impact or ChapterImpactSummaryDTO(),
    )


def to_version_dto(version: ContentVersion) -> ChapterVersionDTO:
    return ChapterVersionDTO(
        version_number=version.version_number,
        content_text=version.content_text,
        created_by=version.created_by,
        change_source=version.change_source,
        change_summary=version.change_summary,
        word_count=version.word_count,
        is_current=version.is_current,
        is_best=version.is_best,
        context_snapshot_hash=version.context_snapshot_hash,
        created_at=version.created_at,
    )
