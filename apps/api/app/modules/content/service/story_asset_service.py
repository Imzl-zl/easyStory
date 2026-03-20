from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.content.models import Content, ContentVersion
from app.modules.project.service import ProjectService
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import AssetType, StoryAssetDTO, StoryAssetSaveDTO

STALE_FROM_OUTLINE = frozenset({"opening_plan", "chapter"})
STALE_FROM_OPENING_PLAN = frozenset({"chapter"})


class StoryAssetService:
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    def save_asset_draft(
        self,
        db: Session,
        project_id: uuid.UUID,
        asset_type: AssetType,
        payload: StoryAssetSaveDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> StoryAssetDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        if asset_type == "opening_plan":
            self._require_approved_asset(db, project_id, "outline")
        content = self._get_asset(db, project_id, asset_type)
        if content is None:
            content = Content(
                project_id=project.id,
                content_type=asset_type,
                title=payload.title,
                status="draft",
            )
            db.add(content)
            db.flush()
        self._append_new_version(content, payload)
        self._mark_stale_dependencies(db, project, asset_type)
        db.commit()
        db.refresh(content)
        return self._to_dto(content)

    def approve_asset(
        self,
        db: Session,
        project_id: uuid.UUID,
        asset_type: AssetType,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> StoryAssetDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        if asset_type == "opening_plan":
            self._require_approved_asset(db, project_id, "outline")
        content = self._require_asset(db, project_id, asset_type)
        current_version = self._current_version(content)
        if current_version is None:
            raise BusinessRuleError(f"{asset_type} 缺少当前版本，无法确认")
        content.status = "approved"
        db.add(content)
        db.commit()
        db.refresh(content)
        return self._to_dto(content)

    def _get_asset(
        self,
        db: Session,
        project_id: uuid.UUID,
        asset_type: AssetType,
    ) -> Content | None:
        return (
            db.query(Content)
            .filter(
                Content.project_id == project_id,
                Content.content_type == asset_type,
            )
            .one_or_none()
        )

    def _require_asset(
        self,
        db: Session,
        project_id: uuid.UUID,
        asset_type: AssetType,
    ) -> Content:
        content = self._get_asset(db, project_id, asset_type)
        if content is None:
            raise NotFoundError(f"{asset_type} not found for project {project_id}")
        return content

    def _require_approved_asset(
        self,
        db: Session,
        project_id: uuid.UUID,
        asset_type: AssetType,
    ) -> Content:
        content = self._get_asset(db, project_id, asset_type)
        if content is None:
            raise BusinessRuleError(f"{asset_type} 必须先确认后才能继续")
        if content.status != "approved":
            raise BusinessRuleError(f"{asset_type} 必须先确认后才能继续")
        return content

    def _append_new_version(
        self,
        content: Content,
        payload: StoryAssetSaveDTO,
    ) -> None:
        for version in content.versions:
            if version.is_current:
                version.is_current = False
        version = ContentVersion(
            content_id=content.id,
            version_number=self._next_version_number(content),
            content_text=payload.content_text,
            created_by=payload.created_by,
            change_source=payload.change_source,
            change_summary=payload.change_summary,
            is_current=True,
            word_count=self._count_text_units(payload.content_text),
        )
        content.title = payload.title
        content.status = "draft"
        content.last_edited_at = datetime.now(timezone.utc)
        content.versions.append(version)

    def _mark_stale_dependencies(
        self,
        db: Session,
        project,
        asset_type: AssetType,
    ) -> None:
        self._mark_downstream_stale(project, asset_type)
        if asset_type in {"outline", "opening_plan"}:
            self._mark_chapter_tasks_stale(db, project.id)

    def _mark_downstream_stale(self, project, asset_type: AssetType) -> None:
        for content in project.contents:
            if content.status != "approved":
                continue
            if self._should_mark_stale(content, asset_type):
                content.status = "stale"

    def _mark_chapter_tasks_stale(self, db: Session, project_id: uuid.UUID) -> None:
        for task in db.query(ChapterTask).filter(ChapterTask.project_id == project_id).all():
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

    def _current_version(self, content: Content) -> ContentVersion | None:
        for version in sorted(content.versions, key=lambda item: item.version_number, reverse=True):
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

    def _count_text_units(self, text: str) -> int:
        return sum(1 for char in text if not char.isspace())
