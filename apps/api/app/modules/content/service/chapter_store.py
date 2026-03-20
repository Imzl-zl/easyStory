from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.content.models import Content
from app.modules.project.models import Project
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .chapter_service_support import CHAPTER_TYPE


def list_chapter_models(
    db: Session,
    project_id: uuid.UUID,
) -> list[Content]:
    return (
        db.query(Content)
        .filter(
            Content.project_id == project_id,
            Content.content_type == CHAPTER_TYPE,
        )
        .order_by(Content.chapter_number.asc())
        .all()
    )


def require_chapter(
    db: Session,
    project_id: uuid.UUID,
    chapter_number: int,
) -> Content:
    content = (
        db.query(Content)
        .filter(
            Content.project_id == project_id,
            Content.content_type == CHAPTER_TYPE,
            Content.chapter_number == chapter_number,
        )
        .one_or_none()
    )
    if content is None:
        raise NotFoundError(f"Chapter not found: project={project_id}, chapter={chapter_number}")
    return content


def get_or_create_chapter(
    db: Session,
    project: Project,
    chapter_number: int,
    title: str,
) -> Content:
    content = (
        db.query(Content)
        .filter(
            Content.project_id == project.id,
            Content.content_type == CHAPTER_TYPE,
            Content.chapter_number == chapter_number,
        )
        .one_or_none()
    )
    if content is not None:
        content.order_index = content.order_index or chapter_number
        return content
    content = Content(
        project_id=project.id,
        content_type=CHAPTER_TYPE,
        title=title,
        chapter_number=chapter_number,
        order_index=chapter_number,
        status="draft",
    )
    db.add(content)
    db.flush()
    return content


def require_preparation_assets_ready(
    db: Session,
    project_id: uuid.UUID,
    asset_types: tuple[str, ...],
) -> None:
    for asset_type in asset_types:
        require_approved_asset(db, project_id, asset_type)


def require_approved_asset(
    db: Session,
    project_id: uuid.UUID,
    asset_type: str,
) -> None:
    asset = (
        db.query(Content)
        .filter(
            Content.project_id == project_id,
            Content.content_type == asset_type,
        )
        .one_or_none()
    )
    if asset is None or asset.status != "approved":
        raise BusinessRuleError(f"{asset_type} 必须先确认后才能继续")
