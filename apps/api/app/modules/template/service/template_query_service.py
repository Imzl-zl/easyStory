from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.template.models import Template, TemplateNode
from app.shared.runtime.errors import NotFoundError

from .dto import (
    TemplateDetailDTO,
    TemplateGuidedQuestionDTO,
    TemplateNodeViewDTO,
    TemplateSummaryDTO,
)


class TemplateQueryService:
    async def list_templates(self, db: AsyncSession) -> list[TemplateSummaryDTO]:
        statement = (
            select(Template)
            .options(selectinload(Template.nodes))
            .order_by(Template.is_builtin.desc(), Template.name.asc(), Template.id.asc())
        )
        templates = (await db.scalars(statement)).all()
        return [self._to_summary(template) for template in templates]

    async def get_template(self, db: AsyncSession, template_id: uuid.UUID) -> TemplateDetailDTO:
        statement = (
            select(Template)
            .options(selectinload(Template.nodes))
            .where(Template.id == template_id)
        )
        template = await db.scalar(statement)
        if template is None:
            raise NotFoundError(f"Template not found: {template_id}")
        return self._to_detail(template)

    def _to_summary(self, template: Template) -> TemplateSummaryDTO:
        return TemplateSummaryDTO(
            id=template.id,
            name=template.name,
            description=template.description,
            genre=template.genre,
            workflow_id=_extract_workflow_id(template.config),
            is_builtin=template.is_builtin,
            node_count=len(template.nodes),
            created_at=template.created_at,
            updated_at=template.updated_at,
        )

    def _to_detail(self, template: Template) -> TemplateDetailDTO:
        return TemplateDetailDTO(
            **self._to_summary(template).model_dump(),
            config=template.config,
            guided_questions=_extract_guided_questions(template.config),
            nodes=[
                TemplateNodeViewDTO(
                    id=node.id,
                    node_order=node.node_order,
                    node_id=_extract_node_id(node.config),
                    node_name=_extract_node_name(node.config),
                    node_type=node.node_type,
                    skill_id=node.skill_id or None,
                    config=node.config,
                    position_x=node.position_x,
                    position_y=node.position_y,
                    ui_config=node.ui_config,
                )
                for node in sorted(template.nodes, key=_node_sort_key)
            ],
        )


def _extract_workflow_id(config: dict[str, Any] | None) -> str | None:
    if not isinstance(config, dict):
        return None
    workflow_id = config.get("workflow_id")
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        return None
    return workflow_id


def _extract_guided_questions(config: dict[str, Any] | None) -> list[TemplateGuidedQuestionDTO]:
    if not isinstance(config, dict):
        return []
    raw_questions = config.get("guided_questions")
    if not isinstance(raw_questions, list):
        return []
    questions: list[TemplateGuidedQuestionDTO] = []
    for item in raw_questions:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        variable = item.get("variable")
        if not isinstance(question, str) or not isinstance(variable, str):
            continue
        questions.append(TemplateGuidedQuestionDTO(question=question, variable=variable))
    return questions


def _extract_node_id(config: dict[str, Any] | None) -> str | None:
    if not isinstance(config, dict):
        return None
    node_id = config.get("id")
    if not isinstance(node_id, str) or not node_id.strip():
        return None
    return node_id


def _extract_node_name(config: dict[str, Any] | None) -> str | None:
    if not isinstance(config, dict):
        return None
    node_name = config.get("name")
    if not isinstance(node_name, str) or not node_name.strip():
        return None
    return node_name


def _node_sort_key(node: TemplateNode) -> tuple[int, str]:
    return (node.node_order, str(node.id))
