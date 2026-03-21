from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app.modules.content.models import Content, ContentVersion
from app.modules.project.models import Project
from app.modules.user.service import TokenService
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_user, ready_project_setting

TEST_JWT_SECRET = "test-jwt-secret"


async def test_chapter_api_supports_save_history_rollback_and_best_version(monkeypatch, tmp_path):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="chapter-api-history")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        headers = _auth_headers(owner_id)
        async with started_async_client(app) as client:
            save_response = await client.put(
                f"/api/v1/projects/{project_id}/chapters/1",
                json={
                    "title": "第一章 逃亡夜",
                    "content_text": "林渊连夜逃离宗门，山门外杀机四伏。",
                    "change_summary": "初版正文",
                },
                headers=headers,
            )
            assert save_response.status_code == 200
            assert save_response.json()["current_version_number"] == 1

            approve_response = await client.post(
                f"/api/v1/projects/{project_id}/chapters/1/approve",
                headers=headers,
            )
            assert approve_response.status_code == 200
            assert approve_response.json()["status"] == "approved"

            best_response = await client.post(
                f"/api/v1/projects/{project_id}/chapters/1/versions/1/best",
                headers=headers,
            )
            assert best_response.status_code == 200
            assert best_response.json()["is_best"] is True

            second_save = await client.put(
                f"/api/v1/projects/{project_id}/chapters/1",
                json={
                    "title": "第一章 逃亡夜",
                    "content_text": "林渊连夜逃离宗门，山门外埋伏比预想更多。",
                    "change_summary": "补强追杀压迫感",
                },
                headers=headers,
            )
            assert second_save.status_code == 200
            assert second_save.json()["current_version_number"] == 2

            versions_response = await client.get(
                f"/api/v1/projects/{project_id}/chapters/1/versions",
                headers=headers,
            )
            assert versions_response.status_code == 200
            assert [item["version_number"] for item in versions_response.json()] == [2, 1]

            rollback_response = await client.post(
                f"/api/v1/projects/{project_id}/chapters/1/versions/1/rollback",
                headers=headers,
            )
            assert rollback_response.status_code == 200
            assert rollback_response.json()["current_version_number"] == 3
            assert rollback_response.json()["content_text"].startswith("林渊连夜逃离宗门")

            clear_best_response = await client.delete(
                f"/api/v1/projects/{project_id}/chapters/1/versions/1/best",
                headers=headers,
            )
            assert clear_best_response.status_code == 200
            assert clear_best_response.json()["is_best"] is False

            chapter_response = await client.get(
                f"/api/v1/projects/{project_id}/chapters/1",
                headers=headers,
            )
            assert chapter_response.status_code == 200
            assert chapter_response.json()["current_version_number"] == 3

            list_response = await client.get(
                f"/api/v1/projects/{project_id}/chapters",
                headers=headers,
            )
            assert list_response.status_code == 200
            assert list_response.json()[0]["best_version_number"] is None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_chapter_api_requires_preparation_assets(monkeypatch, tmp_path):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="chapter-api-assets")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=False)

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/projects/{project_id}/chapters/1",
                json={"title": "第一章", "content_text": "章节正文"},
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 422
            assert "outline 必须先确认后才能继续" in response.json()["detail"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_chapter_api_editing_old_chapter_marks_later_chapters_stale(monkeypatch, tmp_path):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="chapter-api-stale")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    _seed_chapter(session_factory, uuid.UUID(project_id), 1, "第一章", "第一章正文")
    _seed_chapter(session_factory, uuid.UUID(project_id), 2, "第二章", "第二章正文")

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        headers = _auth_headers(owner_id)
        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/projects/{project_id}/chapters/1",
                json={"title": "第一章", "content_text": "第一章重写版"},
                headers=headers,
            )
            assert response.status_code == 200
            assert response.json()["status"] == "draft"

            downstream = await client.get(
                f"/api/v1/projects/{project_id}/chapters/2",
                headers=headers,
            )
            assert downstream.status_code == 200
            assert downstream.json()["status"] == "stale"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _seed_project(
    session_factory: sessionmaker[Session],
    *,
    ready_assets: bool,
) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        project = Project(
            name="章节 API 测试项目",
            owner_id=owner.id,
            project_setting=ready_project_setting(),
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        if ready_assets:
            _create_asset(session, project.id, "outline", "大纲")
            _create_asset(session, project.id, "opening_plan", "开篇设计")
        return str(project.id), owner.id


def _seed_chapter(
    session_factory: sessionmaker[Session],
    project_id: uuid.UUID,
    chapter_number: int,
    title: str,
    content_text: str,
) -> None:
    with session_factory() as session:
        content = Content(
            project_id=project_id,
            content_type="chapter",
            chapter_number=chapter_number,
            title=title,
            order_index=chapter_number,
            status="approved",
        )
        session.add(content)
        session.flush()
        session.add(
            ContentVersion(
                content_id=content.id,
                version_number=1,
                content_text=content_text,
                is_current=True,
            )
        )
        session.commit()


def _create_asset(
    session: Session,
    project_id: uuid.UUID,
    content_type: str,
    title: str,
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
        status="approved",
    )
    session.add(content)
    session.flush()
    session.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=f"{title}内容",
            is_current=True,
        )
    )
    session.commit()


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}
