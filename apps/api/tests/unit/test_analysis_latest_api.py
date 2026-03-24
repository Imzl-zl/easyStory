from __future__ import annotations

from datetime import UTC, datetime

from app.main import create_app
from app.modules.analysis.models import Analysis
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_content, create_project, create_user


async def test_analysis_latest_api_returns_latest_filtered_analysis(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-latest-api")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
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
            project_id = project.id
            owner_id = owner.id
            content_id = content.id
            other_content_id = other_content.id

            session.add_all(
                [
                    Analysis(
                        project_id=project_id,
                        content_id=content_id,
                        analysis_type="style",
                        source_title="样例小说",
                        result={"writing_style": {"rhythm": "fast"}},
                        generated_skill_key="skill.style.river",
                        created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    ),
                    Analysis(
                        project_id=project_id,
                        content_id=content_id,
                        analysis_type="style",
                        source_title="样例小说",
                        result={"writing_style": {"rhythm": "steady"}},
                        generated_skill_key="skill.style.river",
                        created_at=datetime(2026, 1, 2, tzinfo=UTC),
                    ),
                    Analysis(
                        project_id=project_id,
                        content_id=other_content_id,
                        analysis_type="style",
                        source_title="样例小说",
                        result={"writing_style": {"rhythm": "broad"}},
                        generated_skill_key="skill.style.river",
                        created_at=datetime(2026, 1, 3, tzinfo=UTC),
                    ),
                    Analysis(
                        project_id=project_id,
                        content_id=content_id,
                        analysis_type="plot",
                        source_title="样例小说",
                        result={"structure": "双线叙事"},
                        generated_skill_key="skill.style.river",
                        created_at=datetime(2026, 1, 4, tzinfo=UTC),
                    ),
                ]
            )
            session.commit()

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/analyses/latest",
                params={
                    "analysis_type": "style",
                    "content_id": str(content_id),
                    "generated_skill_key": " skill.style.river ",
                },
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 200
            data = response.json()
            assert data["analysis_type"] == "style"
            assert data["content_id"] == str(content_id)
            assert data["generated_skill_key"] == "skill.style.river"
            assert data["result"]["writing_style"]["rhythm"] == "steady"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_latest_api_returns_not_found_when_no_match(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-latest-api-missing")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/analyses/latest",
                params={"analysis_type": "style"},
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 404
            assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_latest_api_rejects_blank_generated_skill_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-latest-api-skill-key-blank")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/analyses/latest",
                params={"generated_skill_key": "   "},
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 422
            assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
