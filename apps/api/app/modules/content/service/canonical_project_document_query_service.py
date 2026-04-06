from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content, ContentVersion
from app.modules.project.service import ProjectService

from .dto import CanonicalProjectDocumentDTO

class CanonicalProjectDocumentQueryService:
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    async def list_canonical_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        include_content: bool = False,
    ) -> list[CanonicalProjectDocumentDTO]:
        if include_content:
            contents = await self._load_canonical_content_models(
                db,
                project_id,
                include_outline=True,
                include_opening_plan=True,
                chapter_numbers=None,
            )
            return [
                _to_canonical_document_dto(content)
                for content in contents
            ]
        rows = await self._load_canonical_document_rows(
            db,
            project_id,
            include_outline=True,
            include_opening_plan=True,
            chapter_numbers=None,
        )
        return [
            CanonicalProjectDocumentDTO(
                project_id=project_id,
                content_id=content_id,
                content_type=content_type,
                title=title,
                chapter_number=chapter_number,
                version_number=version_number,
                word_count=word_count,
                updated_at=_resolve_updated_at(updated_at, version_created_at),
            )
            for (
                chapter_number,
                content_id,
                content_type,
                title,
                updated_at,
                version_created_at,
                version_number,
                word_count,
            ) in rows
        ]

    async def list_selected_canonical_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        include_content: bool = False,
        include_outline: bool = False,
        include_opening_plan: bool = False,
        chapter_numbers: Iterable[int] = (),
    ) -> list[CanonicalProjectDocumentDTO]:
        normalized_chapter_numbers = tuple(sorted(set(chapter_numbers)))
        if not include_outline and not include_opening_plan and not normalized_chapter_numbers:
            return []
        if include_content:
            contents = await self._load_canonical_content_models(
                db,
                project_id,
                include_outline=include_outline,
                include_opening_plan=include_opening_plan,
                chapter_numbers=normalized_chapter_numbers,
            )
            return [
                _to_canonical_document_dto(content)
                for content in contents
            ]
        rows = await self._load_canonical_document_rows(
            db,
            project_id,
            include_outline=include_outline,
            include_opening_plan=include_opening_plan,
            chapter_numbers=normalized_chapter_numbers,
        )
        return [
            CanonicalProjectDocumentDTO(
                project_id=project_id,
                content_id=content_id,
                content_type=content_type,
                title=title,
                chapter_number=chapter_number,
                version_number=version_number,
                word_count=word_count,
                updated_at=_resolve_updated_at(updated_at, version_created_at),
            )
            for (
                chapter_number,
                content_id,
                content_type,
                title,
                updated_at,
                version_created_at,
                version_number,
                word_count,
            ) in rows
        ]

    async def _load_canonical_content_models(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        include_outline: bool,
        include_opening_plan: bool,
        chapter_numbers: tuple[int, ...] | None,
    ) -> list[Content]:
        selection_clause = _build_canonical_content_selection_clause(
            include_outline=include_outline,
            include_opening_plan=include_opening_plan,
            chapter_numbers=chapter_numbers,
        )
        if selection_clause is None:
            return []
        contents = (
            await db.scalars(
                select(Content)
                .options(selectinload(Content.versions))
                .where(
                    Content.project_id == project_id,
                    selection_clause,
                )
            )
        ).all()
        return sorted(contents, key=_canonical_content_sort_key)

    async def _load_canonical_document_rows(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        include_outline: bool,
        include_opening_plan: bool,
        chapter_numbers: tuple[int, ...] | None,
    ):
        selection_clause = _build_canonical_content_selection_clause(
            include_outline=include_outline,
            include_opening_plan=include_opening_plan,
            chapter_numbers=chapter_numbers,
        )
        if selection_clause is None:
            return []
        return (
            await db.execute(
                select(
                    Content.chapter_number,
                    Content.id,
                    Content.content_type,
                    Content.title,
                    Content.last_edited_at,
                    ContentVersion.created_at,
                    ContentVersion.version_number,
                    ContentVersion.word_count,
                )
                .select_from(Content)
                .join(
                    ContentVersion,
                    and_(
                        ContentVersion.content_id == Content.id,
                        ContentVersion.is_current.is_(True),
                    ),
                    isouter=True,
                )
                .where(
                    Content.project_id == project_id,
                    selection_clause,
                )
                .order_by(
                    Content.content_type.asc(),
                    Content.chapter_number.asc().nulls_last(),
                    Content.id.asc(),
                )
            )
        ).all()


def _build_canonical_content_selection_clause(
    *,
    include_outline: bool,
    include_opening_plan: bool,
    chapter_numbers: tuple[int, ...] | None,
):
    clauses = []
    if include_outline:
        clauses.append(Content.content_type == "outline")
    if include_opening_plan:
        clauses.append(Content.content_type == "opening_plan")
    if chapter_numbers is None:
        clauses.append(Content.content_type == "chapter")
    elif chapter_numbers:
        clauses.append(
            and_(
                Content.content_type == "chapter",
                Content.chapter_number.in_(chapter_numbers),
            )
        )
    if not clauses:
        return None
    return or_(*clauses)


def _resolve_updated_at(
    updated_at: datetime | None,
    version_created_at: datetime | None,
) -> datetime | None:
    if updated_at is not None:
        return updated_at
    return version_created_at


def _canonical_content_sort_key(content: Content) -> tuple[int, int]:
    if content.content_type == "outline":
        return (0, 0)
    if content.content_type == "opening_plan":
        return (1, 0)
    return (2, content.chapter_number or 0)


def _to_canonical_document_dto(content: Content) -> CanonicalProjectDocumentDTO:
    version = _resolve_current_version(content)
    return CanonicalProjectDocumentDTO(
        project_id=content.project_id,
        content_id=content.id,
        content_type=content.content_type,
        title=content.title,
        chapter_number=content.chapter_number,
        content_text="" if version is None else version.content_text,
        version_number=None if version is None else version.version_number,
        word_count=None if version is None else version.word_count,
        updated_at=_resolve_updated_at(
            content.last_edited_at,
            None if version is None else version.created_at,
        ),
    )


def _resolve_current_version(content: Content) -> ContentVersion | None:
    for version in sorted(content.versions, key=lambda item: item.version_number, reverse=True):
        if version.is_current:
            return version
    return None
