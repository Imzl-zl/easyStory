from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.template.models import Template, TemplateNode
from app.modules.template.service import (
    create_builtin_template_sync_service,
    create_template_query_service,
    create_template_write_service,
    TemplateCreateDTO,
    TemplateGuidedQuestionDTO,
    TemplateUpdateDTO,
)
from app.modules.project.models import Project
from app.shared.runtime.errors import BusinessRuleError, ConflictError, NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_user


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


async def test_template_write_service_creates_custom_template_with_generated_nodes(tmp_path) -> None:
    write_service = create_template_write_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-write-create")
    )

    try:
        async with async_session_factory() as session:
            detail = await write_service.create_template(
                session,
                TemplateCreateDTO(
                    name="自定义玄幻模板",
                    description="带引导问题的自定义模板",
                    genre="玄幻",
                    workflow_id="workflow.xuanhuan_manual",
                    guided_questions=[
                        TemplateGuidedQuestionDTO(question="主角是谁?", variable="protagonist")
                    ],
                ),
            )

            assert detail.name == "自定义玄幻模板"
            assert detail.is_builtin is False
            assert detail.workflow_id == "workflow.xuanhuan_manual"
            assert [question.variable for question in detail.guided_questions] == ["protagonist"]
            assert [node.node_id for node in detail.nodes] == [
                "outline",
                "opening_plan",
                "chapter_split",
                "chapter_gen",
                "export",
            ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_write_service_rejects_duplicate_name_and_invalid_workflow(tmp_path) -> None:
    sync_service = create_builtin_template_sync_service()
    write_service = create_template_write_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-write-rules")
    )

    try:
        async with async_session_factory() as session:
            await sync_service.sync_builtin_templates(session)

        async with async_session_factory() as session:
            with pytest.raises(ConflictError):
                await write_service.create_template(
                    session,
                    TemplateCreateDTO(
                        name="玄幻小说模板",
                        workflow_id="workflow.xuanhuan_manual",
                    ),
                )

            with pytest.raises(BusinessRuleError):
                await write_service.create_template(
                    session,
                    TemplateCreateDTO(
                        name="不存在的工作流模板",
                        workflow_id="workflow.missing",
                    ),
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_write_service_updates_custom_template_and_rebuilds_nodes(tmp_path) -> None:
    write_service = create_template_write_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-write-update")
    )

    try:
        with session_factory() as session:
            template = Template(
                name="旧模板",
                description="旧描述",
                genre="旧题材",
                config={"workflow_id": "workflow.legacy"},
                is_builtin=False,
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
            session.add(template)
            session.commit()
            session.refresh(template)
            template_id = template.id

        async with async_session_factory() as session:
            detail = await write_service.update_template(
                session,
                template_id,
                TemplateUpdateDTO(
                    name="新模板",
                    description="新描述",
                    genre="玄幻",
                    workflow_id="workflow.xuanhuan_manual",
                    guided_questions=[
                        TemplateGuidedQuestionDTO(
                            question="  冲突是什么?  ",
                            variable=" conflict ",
                        )
                    ],
                ),
            )

            assert detail.name == "新模板"
            assert detail.workflow_id == "workflow.xuanhuan_manual"
            assert [question.question for question in detail.guided_questions] == ["冲突是什么?"]
            assert [question.variable for question in detail.guided_questions] == [
                "core_conflict"
            ]
            assert [node.node_id for node in detail.nodes] == [
                "outline",
                "opening_plan",
                "chapter_split",
                "chapter_gen",
                "export",
            ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_write_service_blocks_builtin_mutation_and_referenced_delete(tmp_path) -> None:
    sync_service = create_builtin_template_sync_service()
    write_service = create_template_write_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-write-guard")
    )

    try:
        async with async_session_factory() as session:
            await sync_service.sync_builtin_templates(session)
            builtin_templates = await create_template_query_service().list_templates(session)
            builtin_template_id = builtin_templates[0].id

            with pytest.raises(BusinessRuleError):
                await write_service.update_template(
                    session,
                    builtin_template_id,
                    TemplateUpdateDTO(
                        name="不允许修改内建模板",
                        workflow_id="workflow.xuanhuan_manual",
                    ),
                )

            with pytest.raises(BusinessRuleError):
                await write_service.delete_template(session, builtin_template_id)

        with session_factory() as session:
            custom_template = Template(
                name="被引用模板",
                config={"workflow_id": "workflow.xuanhuan_manual"},
                is_builtin=False,
            )
            session.add(custom_template)
            session.commit()
            session.refresh(custom_template)
            session.add(Project(name="引用模板的项目", owner_id=create_user(session).id, template_id=custom_template.id))
            session.commit()
            referenced_template_id = custom_template.id

        async with async_session_factory() as session:
            with pytest.raises(ConflictError):
                await write_service.delete_template(session, referenced_template_id)
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _missing_template_id():
    return uuid.UUID("00000000-0000-0000-0000-000000000000")


def _node_sort_key(node: TemplateNode) -> tuple[int, str]:
    return (node.node_order, str(node.id))
