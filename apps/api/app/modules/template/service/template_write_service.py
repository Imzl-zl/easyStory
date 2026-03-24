from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.template.models import Template

from .dto import TemplateCreateDTO, TemplateDetailDTO, TemplateUpdateDTO
from .template_query_service import TemplateQueryService
from .template_write_support import (
    build_template_config,
    build_template_node_payloads,
    ensure_template_deletable,
    ensure_template_mutable,
    ensure_unique_template_name,
    replace_template_nodes,
    require_template,
)


class TemplateWriteService:
    def __init__(
        self,
        config_loader: ConfigLoader,
        *,
        query_service: TemplateQueryService | None = None,
    ) -> None:
        self.config_loader = config_loader
        self.query_service = query_service or TemplateQueryService()

    async def create_template(
        self,
        db: AsyncSession,
        payload: TemplateCreateDTO,
    ) -> TemplateDetailDTO:
        template = Template(
            name=await ensure_unique_template_name(db, payload.name),
            description=_normalize_optional_text(payload.description),
            genre=_normalize_optional_text(payload.genre),
            config=build_template_config(payload.workflow_id, payload.guided_questions),
            is_builtin=False,
        )
        replace_template_nodes(
            template,
            build_template_node_payloads(self.config_loader, payload.workflow_id),
        )
        db.add(template)
        await db.commit()
        return await self.query_service.get_template(db, template.id)

    async def update_template(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        payload: TemplateUpdateDTO,
    ) -> TemplateDetailDTO:
        template = await require_template(db, template_id)
        ensure_template_mutable(template)
        template.name = await ensure_unique_template_name(
            db,
            payload.name,
            exclude_template_id=template.id,
        )
        template.description = _normalize_optional_text(payload.description)
        template.genre = _normalize_optional_text(payload.genre)
        template.config = build_template_config(payload.workflow_id, payload.guided_questions)
        template.nodes.clear()
        await db.flush()
        replace_template_nodes(
            template,
            build_template_node_payloads(self.config_loader, payload.workflow_id),
        )
        await db.commit()
        return await self.query_service.get_template(db, template.id)

    async def delete_template(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> None:
        template = await require_template(db, template_id, load_references=True)
        ensure_template_mutable(template)
        ensure_template_deletable(template)
        await db.delete(template)
        await db.commit()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized
