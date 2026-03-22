from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.analysis.service import AnalysisCreateDTO, AnalysisUpdateDTO, create_analysis_service
from app.shared.runtime.errors import BusinessRuleError, NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_content, create_project, create_user


def test_analysis_create_dto_requires_source_title_without_content_id() -> None:
    with pytest.raises(ValidationError):
        AnalysisCreateDTO(
            analysis_type="style",
            result={"tone": "cold"},
        )


def test_analysis_create_dto_rejects_blank_generated_skill_key() -> None:
    with pytest.raises(ValidationError):
        AnalysisCreateDTO(
            analysis_type="style",
            source_title="样例小说",
            result={"tone": "cold"},
            generated_skill_key="   ",
        )


def test_analysis_update_dto_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError):
        AnalysisUpdateDTO()


async def test_analysis_service_rejects_foreign_content_reference(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-foreign-content")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            other_project = create_project(session, owner=owner)
            foreign_content = create_content(session, project=other_project)
            owner_id = owner.id
            project_id = project.id
            foreign_content_id = foreign_content.id

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError):
                await service.create_analysis(
                    session,
                    project_id,
                    AnalysisCreateDTO(
                        content_id=foreign_content_id,
                        analysis_type="style",
                        result={"tone": "冷峻"},
                    ),
                    owner_id=owner_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_service_backfills_source_title_from_content_title(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-source-title")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第七章：夜雨入城")
            owner_id = owner.id
            project_id = project.id
            content_id = content.id

        async with async_session_factory() as session:
            created = await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    content_id=content_id,
                    analysis_type="style",
                    source_title="   ",
                    result={"tone": "冷峻"},
                ),
                owner_id=owner_id,
            )

        assert created.source_title == "第七章：夜雨入城"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_service_updates_analysis_fields(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-update")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第十章：风雪夜")
            owner_id = owner.id
            project_id = project.id
            content_id = content.id

        async with async_session_factory() as session:
            created = await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    content_id=content_id,
                    analysis_type="style",
                    source_title="旧标题",
                    result={"tone": "冷峻"},
                    suggestions={"keep": ["短句"]},
                    generated_skill_key="skill.style.old",
                ),
                owner_id=owner_id,
            )
            updated = await service.update_analysis(
                session,
                project_id,
                created.id,
                AnalysisUpdateDTO(
                    source_title="   ",
                    analysis_scope={"mode": "sample", "picked_chapters": [1, 3, 5]},
                    result={"writing_style": {"rhythm": "steady"}},
                    suggestions=None,
                    generated_skill_key=" skill.style.updated ",
                ),
                owner_id=owner_id,
            )

        assert updated.source_title == "第十章：风雪夜"
        assert updated.analysis_scope == {"mode": "sample", "picked_chapters": [1, 3, 5]}
        assert updated.result == {"writing_style": {"rhythm": "steady"}}
        assert updated.suggestions is None
        assert updated.generated_skill_key == "skill.style.updated"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_service_rejects_clearing_source_title_without_content(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-update-traceability")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            owner_id = owner.id
            project_id = project.id

        async with async_session_factory() as session:
            created = await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    analysis_type="plot",
                    source_title="样例小说",
                    result={"structure": "双线叙事"},
                ),
                owner_id=owner_id,
            )

            with pytest.raises(BusinessRuleError, match="source_title is required"):
                await service.update_analysis(
                    session,
                    project_id,
                    created.id,
                    AnalysisUpdateDTO(source_title="   "),
                    owner_id=owner_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
