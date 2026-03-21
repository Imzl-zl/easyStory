from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.template.models import Template, TemplateNode
from app.modules.template.service import (
    create_builtin_template_sync_service,
    create_template_query_service,
)
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)


async def test_builtin_template_sync_is_idempotent_and_upgrades_legacy_builtin(tmp_path) -> None:
    sync_service = create_builtin_template_sync_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-sync")
    )
    legacy_template = Template(
        name="玄幻小说模板",
        description="旧模板描述",
        genre="旧题材",
        config={"workflow_id": "workflow.legacy"},
        is_builtin=True,
        nodes=[
            TemplateNode(
                node_order=0,
                node_type="generate",
                skill_id="skill.legacy",
                config={"id": "legacy", "name": "旧节点"},
                position_x=0,
                position_y=0,
                ui_config={"label": "旧节点"},
            )
        ],
    )
    try:
        with session_factory() as session:
            session.add(legacy_template)
            session.commit()
            session.refresh(legacy_template)
            legacy_template_id = legacy_template.id

        async with async_session_factory() as session:
            await sync_service.sync_builtin_templates(session)
            await sync_service.sync_builtin_templates(session)

        async with async_session_factory() as session:
            statement = (
                select(Template)
                .options(selectinload(Template.nodes))
                .where(Template.is_builtin.is_(True))
            )
            templates = (await session.scalars(statement)).all()

            assert len(templates) == 1
            template = templates[0]
            assert template.id == legacy_template_id
            assert template.config == {
                "template_key": "template.xuanhuan",
                "workflow_id": "workflow.xuanhuan_manual",
                "guided_questions": [
                    {"question": "主角是什么身份?", "variable": "protagonist"},
                    {"question": "故事发生在什么世界?", "variable": "world_setting"},
                    {"question": "主要冲突是什么?", "variable": "core_conflict"},
                ],
            }
            assert [node.config["id"] for node in sorted(template.nodes, key=_node_sort_key)] == [
                "outline",
                "opening_plan",
                "chapter_split",
                "chapter_gen",
                "export",
            ]

            export_node = next(node for node in template.nodes if node.config["id"] == "export")
            assert export_node.skill_id == ""
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_query_service_returns_template_detail_with_nullable_export_skill(tmp_path) -> None:
    sync_service = create_builtin_template_sync_service()
    query_service = create_template_query_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-service")
    )

    try:
        async with async_session_factory() as session:
            await sync_service.sync_builtin_templates(session)

        async with async_session_factory() as session:
            templates = await query_service.list_templates(session)

            assert len(templates) == 1
            assert templates[0].name == "玄幻小说模板"
            assert templates[0].workflow_id == "workflow.xuanhuan_manual"
            assert templates[0].node_count == 5

            detail = await query_service.get_template(session, templates[0].id)

            assert [question.variable for question in detail.guided_questions] == [
                "protagonist",
                "world_setting",
                "core_conflict",
            ]
            export_node = next(node for node in detail.nodes if node.node_id == "export")
            assert export_node.node_name == "导出成稿"
            assert export_node.skill_id is None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_query_service_raises_not_found_for_missing_template(tmp_path) -> None:
    query_service = create_template_query_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-service-missing")
    )

    try:
        async with async_session_factory() as session:
            with pytest.raises(NotFoundError):
                await query_service.get_template(session, template_id=_missing_template_id())
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _missing_template_id():
    return uuid.UUID("00000000-0000-0000-0000-000000000000")


def _node_sort_key(node: TemplateNode) -> tuple[int, str]:
    return (node.node_order, str(node.id))
