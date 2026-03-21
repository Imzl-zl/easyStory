from __future__ import annotations

from datetime import UTC, datetime
import uuid

from sqlalchemy.orm import Session

from app.modules.observability.service import AUDIT_ENTITY_PROJECT, AuditLogService
from app.modules.project.models import Project
from app.modules.template.models import Template
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import (
    ProjectCreateDTO,
    ProjectDetailDTO,
    ProjectSummaryDTO,
    ProjectUpdateDTO,
)
from .project_service import ProjectService

PROJECT_DELETE_EVENT = "project_delete"
PROJECT_RESTORE_EVENT = "project_restore"


class ProjectManagementService:
    def __init__(
        self,
        project_service: ProjectService,
        audit_log_service: AuditLogService,
    ) -> None:
        self.project_service = project_service
        self.audit_log_service = audit_log_service

    def create_project(
        self,
        db: Session,
        payload: ProjectCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        template_id = self._resolve_template_id(db, payload.template_id)
        setting = self._dump_project_setting(payload.project_setting)
        project = Project(
            name=payload.name,
            owner_id=owner_id,
            template_id=template_id,
            project_setting=setting,
            allow_system_credential_pool=payload.allow_system_credential_pool,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return self._to_detail(project)

    def list_projects(
        self,
        db: Session,
        *,
        owner_id: uuid.UUID,
        deleted_only: bool = False,
    ) -> list[ProjectSummaryDTO]:
        query = db.query(Project).filter(Project.owner_id == owner_id)
        if deleted_only:
            query = query.filter(Project.deleted_at.is_not(None))
        else:
            query = query.filter(Project.deleted_at.is_(None))
        projects = query.order_by(Project.updated_at.desc(), Project.id.desc()).all()
        return [self._to_summary(project) for project in projects]

    def get_project(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> ProjectDetailDTO:
        project = self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            include_deleted=include_deleted,
        )
        return self._to_detail(project)

    def update_project(
        self,
        db: Session,
        project_id: uuid.UUID,
        payload: ProjectUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self._apply_update(db, project, payload)
        db.add(project)
        db.commit()
        db.refresh(project)
        return self._to_detail(project)

    def soft_delete_project(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        project.deleted_at = datetime.now(UTC)
        self._record_audit(
            db,
            actor_user_id=owner_id,
            event_type=PROJECT_DELETE_EVENT,
            project=project,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return self._to_detail(project)

    def restore_project(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        project = self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            include_deleted=True,
        )
        if project.deleted_at is None:
            raise BusinessRuleError("Project is not deleted")
        project.deleted_at = None
        self._record_audit(
            db,
            actor_user_id=owner_id,
            event_type=PROJECT_RESTORE_EVENT,
            project=project,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return self._to_detail(project)

    def _apply_update(
        self,
        db: Session,
        project: Project,
        payload: ProjectUpdateDTO,
    ) -> None:
        if "name" in payload.model_fields_set:
            if payload.name is None:
                raise BusinessRuleError("Project name cannot be null")
            project.name = payload.name
        if "template_id" in payload.model_fields_set:
            project.template_id = self._resolve_template_id(db, payload.template_id)
        if "allow_system_credential_pool" in payload.model_fields_set:
            project.allow_system_credential_pool = bool(payload.allow_system_credential_pool)

    def _resolve_template_id(
        self,
        db: Session,
        template_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        if template_id is None:
            return None
        template = db.query(Template).filter(Template.id == template_id).one_or_none()
        if template is None:
            raise NotFoundError(f"Template not found: {template_id}")
        return template.id

    def _record_audit(
        self,
        db: Session,
        *,
        actor_user_id: uuid.UUID,
        event_type: str,
        project: Project,
    ) -> None:
        self.audit_log_service.record(
            db,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=AUDIT_ENTITY_PROJECT,
            entity_id=project.id,
            details={
                "name": project.name,
                "owner_id": str(project.owner_id),
                "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
            },
        )

    def _dump_project_setting(self, setting: object) -> dict | None:
        if setting is None:
            return None
        return setting.model_dump(exclude_none=True)

    def _to_summary(
        self,
        project: Project,
    ) -> ProjectSummaryDTO:
        return ProjectSummaryDTO.model_validate(project, from_attributes=True)

    def _to_detail(
        self,
        project: Project,
    ) -> ProjectDetailDTO:
        return ProjectDetailDTO.model_validate(project, from_attributes=True)
