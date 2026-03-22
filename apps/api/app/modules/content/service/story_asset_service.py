from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content, ContentVersion
from app.modules.project.service import ProjectService
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .chapter_store import require_approved_asset
from .dto import AssetType, StoryAssetDTO, StoryAssetSaveDTO, StoryAssetVersionDTO

STALE_FROM_OUTLINE = frozenset({"opening_plan", "chapter"})
STALE_FROM_OPENING_PLAN = frozenset({"chapter"})
STALE_TRIGGER_ASSET_TYPES = frozenset({"outline", "opening_plan"})


class StoryAssetService:
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    async def get_asset(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> StoryAssetDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = await self._require_asset(db, project_id, asset_type)
        return self._to_dto(content)

    async def save_asset_draft(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
        payload: StoryAssetSaveDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> StoryAssetDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_contents=True,
        )
        self.project_service.ensure_setting_allows_preparation(project)
        if asset_type == "opening_plan":
            await require_approved_asset(db, project_id, "outline")
        content = await self._get_asset(db, project_id, asset_type)
        if content is None:
            content = Content(
                project_id=project.id,
                content_type=asset_type,
                title=payload.title,
                status="draft",
                versions=[],
            )
            db.add(content)
            await db.flush()
        self._append_new_version(content, payload)
        await self._mark_stale_dependencies(db, project.id, project.contents, asset_type)
        await db.commit()
        return self._to_dto(content)

    async def list_versions(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[StoryAssetVersionDTO]:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = await self._require_asset(db, project_id, asset_type)
        return [self._to_version_dto(version) for version in self._sorted_versions(content)]

    async def approve_asset(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> StoryAssetDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        if asset_type == "opening_plan":
            await require_approved_asset(db, project_id, "outline")
        content = await self._require_asset(db, project_id, asset_type)
        if self._current_version(content) is None:
            raise BusinessRuleError(f"{asset_type} 缺少当前版本，无法确认")
        content.status = "approved"
        db.add(content)
        await db.commit()
        return self._to_dto(content)

    async def _get_asset(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
    ) -> Content | None:
        statement = (
            select(Content)
            .options(selectinload(Content.versions))
            .where(
                Content.project_id == project_id,
                Content.content_type == asset_type,
            )
        )
        return await db.scalar(statement)

    async def _require_asset(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
    ) -> Content:
        content = await self._get_asset(db, project_id, asset_type)
        if content is None:
            raise NotFoundError(f"{asset_type} not found for project {project_id}")
        return content

    async def _mark_stale_dependencies(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        contents: list[Content],
        asset_type: AssetType,
    ) -> None:
        self._mark_downstream_stale(contents, asset_type)
        if asset_type in STALE_TRIGGER_ASSET_TYPES:
            await self._mark_chapter_tasks_stale(db, project_id)

    def _append_new_version(
        self,
        content: Content,
        payload: StoryAssetSaveDTO,
    ) -> None:
        self._clear_current_version(content)
        content.title = payload.title
        content.status = "draft"
        content.last_edited_at = datetime.now(timezone.utc)
        content.versions.append(
            ContentVersion(
                content_id=content.id,
                version_number=self._next_version_number(content),
                content_text=payload.content_text,
                created_by=payload.created_by,
                change_source=payload.change_source,
                change_summary=payload.change_summary,
                is_current=True,
                word_count=self._count_text_units(payload.content_text),
            )
        )

    def _clear_current_version(self, content: Content) -> None:
        for version in content.versions:
            if version.is_current:
                version.is_current = False

    def _mark_downstream_stale(
        self,
        contents: list[Content],
        asset_type: AssetType,
    ) -> None:
        for content in contents:
            if content.status != "approved":
                continue
            if self._should_mark_stale(content, asset_type):
                content.status = "stale"

    async def _mark_chapter_tasks_stale(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        statement = select(ChapterTask).where(ChapterTask.project_id == project_id)
        tasks = (await db.scalars(statement)).all()
        for task in tasks:
            if task.status != "stale":
                task.status = "stale"

    def _should_mark_stale(self, content: Content, asset_type: AssetType) -> bool:
        if asset_type == "outline":
            return content.content_type in STALE_FROM_OUTLINE
        if content.content_type not in STALE_FROM_OPENING_PLAN:
            return False
        if content.chapter_number is None:
            return False
        return content.chapter_number <= 3

    def _next_version_number(self, content: Content) -> int:
        if not content.versions:
            return 1
        return max(version.version_number for version in content.versions) + 1

    def _sorted_versions(self, content: Content) -> list[ContentVersion]:
        return sorted(content.versions, key=lambda item: item.version_number, reverse=True)

    def _current_version(self, content: Content) -> ContentVersion | None:
        for version in self._sorted_versions(content):
            if version.is_current:
                return version
        return None

    def _to_dto(self, content: Content) -> StoryAssetDTO:
        version = self._current_version(content)
        if version is None:
            raise BusinessRuleError(f"{content.content_type} 缺少当前版本")
        return StoryAssetDTO(
            project_id=content.project_id,
            content_id=content.id,
            content_type=content.content_type,
            title=content.title,
            status=content.status,
            version_number=version.version_number,
            content_text=version.content_text,
        )

    def _to_version_dto(self, version: ContentVersion) -> StoryAssetVersionDTO:
        return StoryAssetVersionDTO(
            version_number=version.version_number,
            content_text=version.content_text,
            created_by=version.created_by,
            change_source=version.change_source,
            change_summary=version.change_summary,
            word_count=version.word_count,
            is_current=version.is_current,
            created_at=version.created_at,
        )

    def _count_text_units(self, text: str) -> int:
        return sum(1 for char in text if not char.isspace())
