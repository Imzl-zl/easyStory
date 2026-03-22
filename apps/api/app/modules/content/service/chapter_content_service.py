from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Content, ContentVersion
from app.modules.context.service import StoryBibleService
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError

from .chapter_mutation_support import (
    build_chapter_impact_summary,
    mark_active_chapter_task_completed,
    mark_downstream_chapters_stale,
)
from .chapter_service_support import (
    PREPARATION_ASSET_TYPES,
    append_chapter_version,
    build_rollback_payload,
    require_current_version,
    require_version,
    sorted_versions,
    to_detail,
    to_summary,
    to_version_dto,
)
from .chapter_store import (
    get_or_create_chapter,
    list_chapter_models,
    require_chapter,
    require_preparation_assets_ready,
)
from .dto import ChapterDetailDTO, ChapterSaveDTO, ChapterSummaryDTO, ChapterVersionDTO


class ChapterContentService:
    def __init__(
        self,
        project_service: ProjectService,
        story_bible_service: StoryBibleService,
    ) -> None:
        self.project_service = project_service
        self.story_bible_service = story_bible_service

    async def list_chapters(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[ChapterSummaryDTO]:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        chapters = await list_chapter_models(db, project_id)
        return [to_summary(content) for content in chapters]

    async def get_chapter(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = await require_chapter(db, project_id, chapter_number)
        return to_detail(content)

    async def save_chapter_draft(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        payload: ChapterSaveDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_contents=True,
        )
        self.project_service.ensure_setting_allows_preparation(project)
        await require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = await get_or_create_chapter(db, project, chapter_number, payload.title)
        append_chapter_version(content, payload)
        stale_chapter_count = mark_downstream_chapters_stale(project, chapter_number)
        await db.commit()
        return to_detail(content, impact=build_chapter_impact_summary(stale_chapter_count))

    async def approve_chapter(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        await require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = await require_chapter(db, project.id, chapter_number)
        require_current_version(content)
        content.status = "approved"
        await mark_active_chapter_task_completed(
            db,
            project.id,
            chapter_number,
            content.id,
        )
        db.add(content)
        await db.commit()
        return to_detail(content)

    async def save_generated_draft(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        title: str,
        content_text: str,
        context_snapshot_hash: str,
    ) -> tuple[Content, ContentVersion]:
        return await self._save_ai_draft(
            db,
            project_id,
            chapter_number,
            title=title,
            content_text=content_text,
            context_snapshot_hash=context_snapshot_hash,
            created_by="ai_assist",
            change_source="ai_generate",
            change_summary="工作流自动生成草稿",
        )

    async def save_auto_fix_draft(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        title: str,
        content_text: str,
        context_snapshot_hash: str,
        change_summary: str = "自动精修最终候选",
    ) -> tuple[Content, ContentVersion]:
        return await self._save_ai_draft(
            db,
            project_id,
            chapter_number,
            title=title,
            content_text=content_text,
            context_snapshot_hash=context_snapshot_hash,
            created_by="auto_fix",
            change_source="ai_fix",
            change_summary=change_summary,
        )

    async def list_versions(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[ChapterVersionDTO]:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = await require_chapter(db, project_id, chapter_number)
        return [to_version_dto(version) for version in sorted_versions(content)]

    async def rollback_version(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        version_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_contents=True,
        )
        self.project_service.ensure_setting_allows_preparation(project)
        await require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = await require_chapter(db, project.id, chapter_number)
        source_version = require_version(content, version_number)
        if source_version.is_current:
            raise BusinessRuleError(f"第{chapter_number}章当前已是版本 v{version_number}")
        append_chapter_version(content, build_rollback_payload(content, source_version))
        await self.story_bible_service.restore_version_facts(
            db,
            project_id=project.id,
            chapter_number=chapter_number,
            source_content_version_id=source_version.id,
        )
        stale_chapter_count = mark_downstream_chapters_stale(project, chapter_number)
        await db.commit()
        return to_detail(content, impact=build_chapter_impact_summary(stale_chapter_count))

    async def mark_best_version(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        version_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterVersionDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = await require_chapter(db, project_id, chapter_number)
        target_version = require_version(content, version_number)
        if target_version.is_best:
            return to_version_dto(target_version)
        self._clear_best_versions(content)
        await db.flush()
        target_version.is_best = True
        await db.commit()
        return to_version_dto(target_version)

    async def clear_best_version(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        version_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterVersionDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = await require_chapter(db, project_id, chapter_number)
        version = require_version(content, version_number)
        if not version.is_best:
            raise BusinessRuleError(f"第{chapter_number}章的版本 v{version_number} 不是最佳版本")
        version.is_best = False
        await db.commit()
        return to_version_dto(version)

    async def _save_ai_draft(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        title: str,
        content_text: str,
        context_snapshot_hash: str,
        created_by: str,
        change_source: str,
        change_summary: str,
    ) -> tuple[Content, ContentVersion]:
        project = await self.project_service.require_project(
            db,
            project_id,
            load_contents=True,
        )
        self.project_service.ensure_setting_allows_preparation(project)
        await require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = await get_or_create_chapter(db, project, chapter_number, title)
        append_chapter_version(
            content,
            ChapterSaveDTO(
                title=title,
                content_text=content_text,
                created_by=created_by,
                change_source=change_source,
                change_summary=change_summary,
                context_snapshot_hash=context_snapshot_hash,
            ),
        )
        mark_downstream_chapters_stale(project, chapter_number)
        await db.flush()
        return content, require_current_version(content)

    def _clear_best_versions(self, content: Content) -> None:
        for version in content.versions:
            if version.is_best:
                version.is_best = False
