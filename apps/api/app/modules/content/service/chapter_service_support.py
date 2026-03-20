from __future__ import annotations

from app.modules.content.models import Content, ContentVersion
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import ChapterDetailDTO, ChapterSummaryDTO, ChapterVersionDTO

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
        best_version_number=best_version_number(content),
        word_count=version.word_count,
        last_edited_at=content.last_edited_at,
    )


def to_detail(content: Content) -> ChapterDetailDTO:
    version = require_current_version(content)
    summary = to_summary(content)
    return ChapterDetailDTO(
        **summary.model_dump(),
        content_text=version.content_text,
        change_summary=version.change_summary,
        created_by=version.created_by,
        change_source=version.change_source,
        context_snapshot_hash=version.context_snapshot_hash,
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
