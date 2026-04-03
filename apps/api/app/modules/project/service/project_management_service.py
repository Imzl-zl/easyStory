from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.models import Project
from app.modules.template.models import Template
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import ProjectCreateDTO, ProjectDetailDTO, ProjectSummaryDTO, ProjectUpdateDTO
from .project_service import ProjectService

if TYPE_CHECKING:
    from app.modules.content.service import StoryAssetService


class ProjectManagementService:
    def __init__(
        self,
        project_service: ProjectService,
        story_asset_service: StoryAssetService,
    ) -> None:
        self.project_service = project_service
        self.story_asset_service = story_asset_service

    async def create_project(
        self,
        db: AsyncSession,
        payload: ProjectCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        project = Project(
            name=payload.name,
            owner_id=owner_id,
            template_id=await self._resolve_template_id(db, payload.template_id),
            project_setting=self._dump_project_setting(payload.project_setting),
            allow_system_credential_pool=payload.allow_system_credential_pool,
        )
        db.add(project)
        await db.flush()
        await self.story_asset_service.scaffold_preparation_assets(db, project.id)
        await db.commit()
        await db.refresh(project)
        await self.project_service.ensure_project_document_template(db, project.id, owner_id=owner_id)
        return self._to_detail(project)

    async def list_projects(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        deleted_only: bool = False,
    ) -> list[ProjectSummaryDTO]:
        statement = select(Project).where(Project.owner_id == owner_id)
        deleted_filter = Project.deleted_at.is_not(None) if deleted_only else Project.deleted_at.is_(None)
        projects = (await db.scalars(statement.where(deleted_filter).order_by(Project.updated_at.desc(), Project.id.desc()))).all()
        return [self._to_summary(project) for project in projects]

    async def get_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> ProjectDetailDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            include_deleted=include_deleted,
        )
        return self._to_detail(project)

    async def update_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ProjectUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        if "name" in payload.model_fields_set:
            if payload.name is None:
                raise BusinessRuleError("Project name cannot be null")
            project.name = payload.name
        if "template_id" in payload.model_fields_set:
            project.template_id = await self._resolve_template_id(db, payload.template_id)
        if "allow_system_credential_pool" in payload.model_fields_set:
            project.allow_system_credential_pool = bool(payload.allow_system_credential_pool)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return self._to_detail(project)

    async def _resolve_template_id(
        self,
        db: AsyncSession,
        template_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        if template_id is None:
            return None
        template = await db.scalar(select(Template).where(Template.id == template_id))
        if template is None:
            raise NotFoundError(f"Template not found: {template_id}")
        return template.id

    def _dump_project_setting(self, setting: object) -> dict | None:
        if setting is None:
            return None
        return setting.model_dump(exclude_none=True)

    def _to_summary(self, project: Project) -> ProjectSummaryDTO:
        return ProjectSummaryDTO.model_validate(project, from_attributes=True)

    def _to_detail(self, project: Project) -> ProjectDetailDTO:
        return ProjectDetailDTO.model_validate(project, from_attributes=True)
