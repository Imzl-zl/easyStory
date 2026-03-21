from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content
from app.modules.project.models import Project
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .chapter_service_support import CHAPTER_TYPE


async def list_chapter_models(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[Content]:
    statement = _chapter_statement(project_id).order_by(Content.chapter_number.asc())
    return (await db.scalars(statement)).all()


async def require_chapter(
    db: AsyncSession,
    project_id: uuid.UUID,
    chapter_number: int,
) -> Content:
    statement = _chapter_statement(project_id).where(Content.chapter_number == chapter_number)
    content = await db.scalar(statement)
    if content is None:
        raise NotFoundError(f"Chapter not found: project={project_id}, chapter={chapter_number}")
    return content


async def get_or_create_chapter(
    db: AsyncSession,
    project: Project,
    chapter_number: int,
    title: str,
) -> Content:
    statement = _chapter_statement(project.id).where(Content.chapter_number == chapter_number)
    content = await db.scalar(statement)
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
        versions=[],
    )
    db.add(content)
    await db.flush()
    return content

async def require_preparation_assets_ready(
    db: AsyncSession,
    project_id: uuid.UUID,
    asset_types: tuple[str, ...],
) -> None:
    for asset_type in asset_types:
        await require_approved_asset(db, project_id, asset_type)


async def require_approved_asset(
    db: AsyncSession,
    project_id: uuid.UUID,
    asset_type: str,
) -> None:
    statement = select(Content).where(
        Content.project_id == project_id,
        Content.content_type == asset_type,
    )
    asset = await db.scalar(statement)
    if asset is None or asset.status != "approved":
        raise BusinessRuleError(f"{asset_type} 必须先确认后才能继续")


def _chapter_statement(project_id: uuid.UUID):
    return (
        select(Content)
        .options(selectinload(Content.versions))
        .where(
            Content.project_id == project_id,
            Content.content_type == CHAPTER_TYPE,
        )
    )
