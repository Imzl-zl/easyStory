from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.content.models import Content, ContentVersion
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError

from .chapter_service_support import (
    PREPARATION_ASSET_TYPES,
    count_text_units,
    require_current_version,
    require_version,
    sorted_versions,
    to_detail,
    to_summary,
    to_version_dto,
)
from .chapter_mutation_support import mark_active_chapter_task_completed, mark_downstream_chapters_stale
from .chapter_store import (
    get_or_create_chapter,
    list_chapter_models,
    require_chapter,
    require_preparation_assets_ready,
)
from .dto import ChapterDetailDTO, ChapterSaveDTO, ChapterSummaryDTO, ChapterVersionDTO

class ChapterContentService:
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    def list_chapters(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[ChapterSummaryDTO]:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        chapters = list_chapter_models(db, project_id)
        return [to_summary(content) for content in chapters]

    def get_chapter(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = require_chapter(db, project_id, chapter_number)
        return to_detail(content)

    def save_chapter_draft(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        payload: ChapterSaveDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = get_or_create_chapter(db, project, chapter_number, payload.title)
        self._append_new_version(content, payload)
        mark_downstream_chapters_stale(project, chapter_number)
        db.commit()
        db.refresh(content)
        return to_detail(content)
    def approve_chapter(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = require_chapter(db, project.id, chapter_number)
        require_current_version(content)
        content.status = "approved"
        mark_active_chapter_task_completed(db, project.id, chapter_number, content.id)
        db.add(content)
        db.commit()
        db.refresh(content)
        return to_detail(content)
    def save_generated_draft(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        title: str,
        content_text: str,
        context_snapshot_hash: str,
    ) -> tuple[Content, ContentVersion]:
        return self._save_ai_draft(
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
    def save_auto_fix_draft(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        title: str,
        content_text: str,
        context_snapshot_hash: str,
        change_summary: str = "自动精修最终候选",
    ) -> tuple[Content, ContentVersion]:
        return self._save_ai_draft(
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
    def _save_ai_draft(
        self,
        db: Session,
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
        project = self.project_service.require_project(db, project_id)
        self.project_service.ensure_setting_allows_preparation(project)
        require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = get_or_create_chapter(db, project, chapter_number, title)
        self._append_new_version(
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
        db.flush()
        return content, require_current_version(content)
    def list_versions(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[ChapterVersionDTO]:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = require_chapter(db, project_id, chapter_number)
        return [to_version_dto(version) for version in sorted_versions(content)]
    def rollback_version(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        version_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterDetailDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        require_preparation_assets_ready(db, project.id, PREPARATION_ASSET_TYPES)
        content = require_chapter(db, project.id, chapter_number)
        source_version = require_version(content, version_number)
        if source_version.is_current:
            raise BusinessRuleError(f"第{chapter_number}章当前已是版本 v{version_number}")
        payload = self._build_rollback_payload(content, source_version)
        self._append_new_version(content, payload)
        mark_downstream_chapters_stale(project, chapter_number)
        db.commit()
        db.refresh(content)
        return to_detail(content)
    def mark_best_version(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        version_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterVersionDTO:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = require_chapter(db, project_id, chapter_number)
        self._set_best_version(db, content, version_number)
        db.commit()
        db.refresh(content)
        version = require_version(content, version_number)
        return to_version_dto(version)
    def clear_best_version(
        self,
        db: Session,
        project_id: uuid.UUID,
        chapter_number: int,
        version_number: int,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ChapterVersionDTO:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        content = require_chapter(db, project_id, chapter_number)
        version = require_version(content, version_number)
        if not version.is_best:
            raise BusinessRuleError(f"第{chapter_number}章的版本 v{version_number} 不是最佳版本")
        version.is_best = False
        db.commit()
        db.refresh(content)
        version = require_version(content, version_number)
        return to_version_dto(version)
    def _append_new_version(
        self,
        content: Content,
        payload: ChapterSaveDTO,
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
                is_best=False,
                word_count=count_text_units(payload.content_text),
                context_snapshot_hash=payload.context_snapshot_hash,
            )
        )
    def _clear_current_version(self, content: Content) -> None:
        for version in content.versions:
            if version.is_current:
                version.is_current = False
    def _set_best_version(
        self,
        db: Session,
        content: Content,
        version_number: int,
    ) -> None:
        target_version = require_version(content, version_number)
        if target_version.is_best:
            return
        for version in content.versions:
            if version.is_best:
                version.is_best = False
        db.flush()
        target_version.is_best = True
    def _build_rollback_payload(
        self,
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
    def _next_version_number(self, content: Content) -> int:
        if not content.versions:
            return 1
        return max(version.version_number for version in content.versions) + 1
