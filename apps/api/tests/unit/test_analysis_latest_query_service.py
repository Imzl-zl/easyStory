from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.analysis.models import Analysis
from app.modules.analysis.service import AnalysisCreateDTO, create_analysis_service
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_content, create_project, create_user


async def _set_analysis_created_at(
    session,
    analysis_id,
    created_at: datetime,
) -> None:
    analysis = await session.get(Analysis, analysis_id)
    assert analysis is not None
    analysis.created_at = created_at
    session.add(analysis)


async def test_analysis_service_gets_latest_analysis_for_filters(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-latest")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第一章")
            other_content = create_content(
                session,
                project=project,
                title="第二章",
                chapter_number=2,
            )
            owner_id = owner.id
            project_id = project.id
            content_id = content.id
            other_content_id = other_content.id

        async with async_session_factory() as session:
            first = await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    content_id=content_id,
                    analysis_type="style",
                    source_title="样例小说",
                    result={"writing_style": {"rhythm": "fast"}},
                    generated_skill_key="skill.style.river",
                ),
                owner_id=owner_id,
            )
            expected = await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    content_id=content_id,
                    analysis_type="style",
                    source_title="样例小说",
                    result={"writing_style": {"rhythm": "steady"}},
                    generated_skill_key="skill.style.river",
                ),
                owner_id=owner_id,
            )
            other_content_match = await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    content_id=other_content_id,
                    analysis_type="style",
                    source_title="样例小说",
                    result={"writing_style": {"rhythm": "broad"}},
                    generated_skill_key="skill.style.river",
                ),
                owner_id=owner_id,
            )
            other_type_match = await service.create_analysis(
                session,
                project_id,
                AnalysisCreateDTO(
                    content_id=content_id,
                    analysis_type="plot",
                    source_title="样例小说",
                    result={"structure": "双线叙事"},
                    generated_skill_key="skill.style.river",
                ),
                owner_id=owner_id,
            )

            await _set_analysis_created_at(session, first.id, datetime(2026, 1, 1, tzinfo=UTC))
            await _set_analysis_created_at(session, expected.id, datetime(2026, 1, 2, tzinfo=UTC))
            await _set_analysis_created_at(
                session,
                other_content_match.id,
                datetime(2026, 1, 3, tzinfo=UTC),
            )
            await _set_analysis_created_at(
                session,
                other_type_match.id,
                datetime(2026, 1, 4, tzinfo=UTC),
            )
            await session.commit()

            latest = await service.get_latest_analysis(
                session,
                project_id,
                owner_id=owner_id,
                analysis_type="style",
                content_id=content_id,
                generated_skill_key=" skill.style.river ",
            )

        assert latest.id == expected.id
        assert latest.result["writing_style"]["rhythm"] == "steady"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_service_raises_not_found_when_latest_query_has_no_match(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-latest-missing")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            owner_id = owner.id
            project_id = project.id

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError, match="Analysis not found for provided filters"):
                await service.get_latest_analysis(
                    session,
                    project_id,
                    owner_id=owner_id,
                    analysis_type="style",
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
