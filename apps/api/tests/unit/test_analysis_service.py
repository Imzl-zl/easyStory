from __future__ import annotations

import pytest

from app.modules.analysis.service import AnalysisCreateDTO, create_analysis_service
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_content, create_project, create_user


async def test_analysis_service_creates_lists_and_gets_project_analysis(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="样例章节")
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
                    source_title="样例小说",
                    analysis_scope={"mode": "chapter_range", "chapters": [1, 2, 3]},
                    result={"writing_style": {"rhythm": "fast"}},
                    suggestions={"keep": ["短句"]},
                ),
                owner_id=owner_id,
            )
            await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    analysis_type="plot",
                    source_title="样例小说",
                    analysis_scope={"mode": "sample"},
                    result={"structure": "双线叙事"},
                ),
                owner_id=owner_id,
            )

            summaries = await service.list_analyses(
                session,
                project_id,
                owner_id=owner_id,
                analysis_type="style",
                content_id=content_id,
            )
            detail = await service.get_analysis(
                session,
                project_id,
                created.id,
                owner_id=owner_id,
            )

        assert created.project_id == project_id
        assert created.content_id == content_id
        assert created.analysis_scope == {"mode": "chapter_range", "chapters": [1, 2, 3]}
        assert len(summaries) == 1
        assert summaries[0].analysis_type == "style"
        assert detail.result["writing_style"]["rhythm"] == "fast"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


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


async def test_analysis_service_hides_other_users_project(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-owner")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            outsider_id = outsider.id
            project_id = project.id

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError):
                await service.list_analyses(session, project_id, owner_id=outsider_id)
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
