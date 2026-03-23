from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.config_registry import ConfigLoader
from app.modules.template.models import Template, TemplateNode
from app.shared.runtime.errors import (
    BusinessRuleError,
    ConfigurationError,
    ConflictError,
    NotFoundError,
)

from .builtin_catalog import DEFAULT_TEMPLATE_NODE_X_GAP, DEFAULT_TEMPLATE_NODE_Y
from .dto import TemplateGuidedQuestionDTO

EMPTY_TEMPLATE_NODE_SKILL_ID = ""


async def require_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    *,
    load_references: bool = False,
) -> Template:
    options = [selectinload(Template.nodes)]
    if load_references:
        options.extend(
            [
                selectinload(Template.projects),
                selectinload(Template.workflow_executions),
            ]
        )
    statement = select(Template).options(*options).where(Template.id == template_id)
    template = await db.scalar(statement)
    if template is None:
        raise NotFoundError(f"Template not found: {template_id}")
    return template


def ensure_template_mutable(template: Template) -> None:
    if template.is_builtin:
        raise BusinessRuleError("内建模板只读，不允许修改或删除")


async def ensure_unique_template_name(
    db: AsyncSession,
    name: str,
    *,
    exclude_template_id: uuid.UUID | None = None,
) -> str:
    normalized_name = name.strip()
    statement = select(Template.id).where(func.lower(Template.name) == normalized_name.lower())
    if exclude_template_id is not None:
        statement = statement.where(Template.id != exclude_template_id)
    existing_id = await db.scalar(statement.limit(1))
    if existing_id is not None:
        raise ConflictError(f"模板名称已存在: {normalized_name}")
    return normalized_name


def build_template_config(
    workflow_id: str,
    guided_questions: Sequence[TemplateGuidedQuestionDTO],
    *,
    template_key: str | None = None,
) -> dict[str, object]:
    config: dict[str, object] = {
        "workflow_id": workflow_id.strip(),
        "guided_questions": [
            {
                "question": question.question.strip(),
                "variable": question.variable.strip(),
            }
            for question in guided_questions
        ],
    }
    if template_key is not None:
        config["template_key"] = template_key
    return config


def build_template_node_payloads(
    config_loader: ConfigLoader,
    workflow_id: str,
) -> list[dict[str, object]]:
    try:
        workflow = config_loader.load_workflow(workflow_id.strip())
    except ConfigurationError as exc:
        raise BusinessRuleError(str(exc)) from exc
    return [
        {
            "node_order": index,
            "node_type": node.node_type,
            "skill_id": normalize_skill_id(node.skill),
            "config": build_template_node_config(
                node.model_dump(by_alias=True, exclude_none=True)
            ),
            "position_x": index * DEFAULT_TEMPLATE_NODE_X_GAP,
            "position_y": DEFAULT_TEMPLATE_NODE_Y,
            "ui_config": {"label": node.name},
        }
        for index, node in enumerate(workflow.nodes)
    ]


def replace_template_nodes(
    template: Template,
    node_payloads: Sequence[dict[str, object]],
) -> None:
    template.nodes = [TemplateNode(**payload) for payload in node_payloads]


def ensure_template_deletable(template: Template) -> None:
    if template.projects:
        raise ConflictError("模板仍被项目引用，不能删除")
    if template.workflow_executions:
        raise ConflictError("模板仍被工作流执行引用，不能删除")


def build_template_node_config(raw_config: dict[str, object]) -> dict[str, object]:
    node_config = dict(raw_config)
    node_config.pop("type", None)
    node_config.pop("skill", None)
    return node_config


def normalize_skill_id(skill_id: str | None) -> str:
    if skill_id is None:
        return EMPTY_TEMPLATE_NODE_SKILL_ID
    normalized = skill_id.strip()
    if not normalized:
        return EMPTY_TEMPLATE_NODE_SKILL_ID
    return normalized
