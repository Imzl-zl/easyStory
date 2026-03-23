from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.config_registry import ConfigLoader
from app.modules.template.models import Template, TemplateNode

from .builtin_catalog import BUILTIN_TEMPLATE_SPECS, BuiltinTemplateSpec
from .dto import TemplateGuidedQuestionDTO
from .template_write_support import (
    build_template_config,
    build_template_node_payloads,
    replace_template_nodes,
)


class BuiltinTemplateSyncService:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    async def sync_builtin_templates(self, db: AsyncSession) -> None:
        templates = (await db.scalars(_builtin_templates_statement())).all()
        existing_by_key = {
            template_key: template
            for template in templates
            if (template_key := _extract_template_key(template.config)) is not None
        }
        existing_by_name = {template.name: template for template in templates}
        changed = False
        for spec in BUILTIN_TEMPLATE_SPECS:
            expected_config = self._build_template_config(spec)
            expected_nodes = build_template_node_payloads(self.config_loader, spec.workflow_id)
            template = existing_by_key.get(spec.template_key) or existing_by_name.get(spec.name)
            if template is None:
                db.add(
                    Template(
                        name=spec.name,
                        description=spec.description,
                        genre=spec.genre,
                        config=expected_config,
                        is_builtin=True,
                        nodes=[TemplateNode(**payload) for payload in expected_nodes],
                    )
                )
                changed = True
                continue
            if await self._sync_existing_template(
                db,
                template,
                spec=spec,
                expected_config=expected_config,
                expected_nodes=expected_nodes,
            ):
                changed = True
        if changed:
            await db.commit()

    async def _sync_existing_template(
        self,
        db: AsyncSession,
        template: Template,
        *,
        spec: BuiltinTemplateSpec,
        expected_config: dict[str, Any],
        expected_nodes: list[dict[str, Any]],
    ) -> bool:
        current_nodes = [self._serialize_node(node) for node in sorted(template.nodes, key=_node_sort_key)]
        if (
            template.description == spec.description
            and template.genre == spec.genre
            and template.config == expected_config
            and template.is_builtin is True
            and current_nodes == expected_nodes
        ):
            return False
        template.description = spec.description
        template.genre = spec.genre
        template.config = expected_config
        template.is_builtin = True
        template.nodes.clear()
        await db.flush()
        replace_template_nodes(template, expected_nodes)
        return True

    def _build_template_config(self, spec: BuiltinTemplateSpec) -> dict[str, Any]:
        return build_template_config(
            spec.workflow_id,
            [
                TemplateGuidedQuestionDTO(question=question, variable=variable)
                for question, variable in spec.guided_questions
            ],
            template_key=spec.template_key,
        )

    def _serialize_node(self, node: TemplateNode) -> dict[str, Any]:
        return {
            "node_order": node.node_order,
            "node_type": node.node_type,
            "skill_id": node.skill_id,
            "config": node.config,
            "position_x": node.position_x,
            "position_y": node.position_y,
            "ui_config": node.ui_config,
        }


def _builtin_templates_statement():
    return (
        select(Template)
        .options(selectinload(Template.nodes))
        .where(Template.is_builtin.is_(True))
    )


def _extract_template_key(config: dict[str, Any] | None) -> str | None:
    if not isinstance(config, dict):
        return None
    template_key = config.get("template_key")
    if not isinstance(template_key, str):
        return None
    normalized = template_key.strip()
    if not normalized:
        return None
    return normalized


def _node_sort_key(node: TemplateNode) -> tuple[int, str]:
    return (node.node_order, str(node.id))
