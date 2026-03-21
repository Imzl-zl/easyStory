from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.unit.models.helpers import create_content, create_project, create_user
from tests.unit.test_workflow_api import _auth_headers, _build_session_factory

TEST_JWT_SECRET = "test-jwt-secret"


def test_analysis_api_creates_lists_and_gets_analysis(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第一章")
            project_id = project.id
            content_id = content.id
            owner_id = owner.id

        create_response = client.post(
            f"/api/v1/projects/{project_id}/analyses",
            json={
                "content_id": str(content_id),
                "analysis_type": "style",
                "source_title": "样例小说",
                "analysis_scope": {"mode": "chapter_range", "chapters": [1, 2]},
                "result": {"writing_style": {"vocabulary": "华丽"}},
                "suggestions": {"keep": ["对话感"]},
            },
            headers=_auth_headers(owner_id),
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["analysis_type"] == "style"
        assert created["content_id"] == str(content_id)

        list_response = client.get(
            f"/api/v1/projects/{project_id}/analyses",
            params={"analysis_type": "style", "content_id": str(content_id)},
            headers=_auth_headers(owner_id),
        )
        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed) == 1
        assert listed[0]["id"] == created["id"]

        detail_response = client.get(
            f"/api/v1/projects/{project_id}/analyses/{created['id']}",
            headers=_auth_headers(owner_id),
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["result"]["writing_style"]["vocabulary"] == "华丽"
    finally:
        client.close()
        engine.dispose()


def test_analysis_api_hides_other_users_project(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))

    try:
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            outsider_id = outsider.id

        response = client.get(
            f"/api/v1/projects/{project_id}/analyses",
            headers=_auth_headers(outsider_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()


def test_analysis_api_rejects_foreign_content_reference(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            other_project = create_project(session, owner=owner)
            foreign_content = create_content(session, project=other_project)
            project_id = project.id
            owner_id = owner.id

        response = client.post(
            f"/api/v1/projects/{project_id}/analyses",
            json={
                "content_id": str(foreign_content.id),
                "analysis_type": "style",
                "result": {"writing_style": {"vocabulary": "华丽"}},
            },
            headers=_auth_headers(owner_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()
