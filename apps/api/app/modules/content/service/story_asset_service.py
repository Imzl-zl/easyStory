from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content, ContentVersion
from app.modules.project.service import ProjectService
from app.modules.project.service.project_document_version_support import (
    build_project_canonical_document_version,
)
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .chapter_store import require_approved_asset
from .dto import (
    AssetType,
    StoryAssetDTO,
    StoryAssetMutationDTO,
    StoryAssetSaveDTO,
    StoryAssetVersionDTO,
)
from .story_asset_service_support import (
    STALE_TRIGGER_ASSET_TYPES,
    build_story_asset_impact_summary,
    build_story_asset_mutation,
    mark_downstream_stale,
)
PREPARATION_ASSET_TITLES: dict[AssetType, str] = {
    "outline": "大纲",
    "opening_plan": "开篇设计",
}
SCAFFOLD_VERSION_TEXT = ""
SCAFFOLD_VERSION_CHANGE_SUMMARY = "系统初始化前置资产骨架"
SCAFFOLD_VERSION_CREATED_BY = "system"
SCAFFOLD_VERSION_CHANGE_SOURCE = "import"


class StoryAssetService:
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    async def scaffold_preparation_assets(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        for asset_type, title in PREPARATION_ASSET_TITLES.items():
            db.add(self._build_scaffold_asset(project_id, asset_type, title))

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
    ) -> StoryAssetMutationDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_contents=True,
        )
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
        impact = await self._mark_stale_dependencies(db, project.id, project.contents, asset_type)
        await db.commit()
        return build_story_asset_mutation(self._to_dto(content), impact)

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
    ) -> StoryAssetMutationDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        if asset_type == "opening_plan":
            await require_approved_asset(db, project_id, "outline")
        content = await self._require_asset(db, project_id, asset_type)
        self._require_approvable_version(asset_type, self._current_version(content))
        content.status = "approved"
        db.add(content)
        await db.commit()
        return build_story_asset_mutation(self._to_dto(content))

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
    ):
        content_impacts = mark_downstream_stale(contents, asset_type)
        stale_chapter_task_count = 0
        if asset_type in STALE_TRIGGER_ASSET_TYPES:
            stale_chapter_task_count = await self._mark_chapter_tasks_stale(db, project_id)
        return build_story_asset_impact_summary(
            asset_type,
            content_impacts,
            stale_chapter_task_count=stale_chapter_task_count,
        )

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

    def _build_scaffold_asset(
        self,
        project_id: uuid.UUID,
        asset_type: AssetType,
        title: str,
    ) -> Content:
        return Content(
            project_id=project_id,
            content_type=asset_type,
            title=title,
            status="draft",
            versions=[self._build_scaffold_version()],
        )

    def _build_scaffold_version(self) -> ContentVersion:
        return ContentVersion(
            version_number=1,
            content_text=SCAFFOLD_VERSION_TEXT,
            created_by=SCAFFOLD_VERSION_CREATED_BY,
            change_source=SCAFFOLD_VERSION_CHANGE_SOURCE,
            change_summary=SCAFFOLD_VERSION_CHANGE_SUMMARY,
            is_current=True,
            word_count=0,
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
    ) -> int:
        statement = select(ChapterTask).where(ChapterTask.project_id == project_id)
        tasks = (await db.scalars(statement)).all()
        stale_task_count = 0
        for task in tasks:
            if task.status != "stale":
                task.status = "stale"
                stale_task_count += 1
        return stale_task_count

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

    def _require_approvable_version(
        self,
        asset_type: AssetType,
        version: ContentVersion | None,
    ) -> None:
        if version is None:
            raise BusinessRuleError(f"{asset_type} 缺少当前版本，无法确认")
        if self._count_text_units(version.content_text) == 0:
            raise BusinessRuleError(f"{asset_type} 内容为空，无法确认")

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
            document_version=build_project_canonical_document_version(
                f"canonical:{content.content_type}",
                content_id=content.id,
                version_number=version.version_number,
            ),
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
