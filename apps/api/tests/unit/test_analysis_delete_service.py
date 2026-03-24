from __future__ import annotations

import pytest

from app.modules.analysis.service import AnalysisCreateDTO, create_analysis_service
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_project, create_user


async def test_analysis_service_deletes_analysis(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-delete")
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
            await service.delete_analysis(
                session,
                project_id,
                created.id,
                owner_id=owner_id,
            )

            with pytest.raises(NotFoundError):
                await service.get_analysis(
                    session,
                    project_id,
                    created.id,
                    owner_id=owner_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_service_hides_other_users_project_on_delete(tmp_path) -> None:
    service = create_analysis_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-service-delete-owner")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            owner_id = owner.id
            outsider_id = outsider.id
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

            with pytest.raises(NotFoundError):
                await service.delete_analysis(
                    session,
                    project_id,
                    created.id,
                    owner_id=outsider_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
