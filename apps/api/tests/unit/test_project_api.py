from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.unit.models.helpers import create_project, create_template, create_user, ready_project_setting
from tests.unit.test_workflow_api import TEST_JWT_SECRET, _auth_headers, _build_session_factory


def test_project_api_manages_project_lifecycle(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))

    try:
        with session_factory() as session:
            owner = create_user(session)
            template = create_template(session)
            owner_id = owner.id
            template_id = template.id

        create_response = client.post(
            "/api/v1/projects",
            json={
                "name": "接口项目",
                "template_id": str(template_id),
                "project_setting": ready_project_setting(),
                "allow_system_credential_pool": True,
            },
            headers=_auth_headers(owner_id),
        )
        assert create_response.status_code == 200
        created = create_response.json()
        project_id = created["id"]
        assert created["genre"] == "玄幻"
        assert created["template_id"] == str(template_id)

        list_response = client.get("/api/v1/projects", headers=_auth_headers(owner_id))
        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed) == 1
        assert listed[0]["id"] == project_id

        detail_response = client.get(
            f"/api/v1/projects/{project_id}",
            headers=_auth_headers(owner_id),
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["name"] == "接口项目"

        update_response = client.put(
            f"/api/v1/projects/{project_id}",
            json={
                "name": "接口项目-更新",
                "allow_system_credential_pool": False,
                "template_id": None,
            },
            headers=_auth_headers(owner_id),
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "接口项目-更新"
        assert updated["allow_system_credential_pool"] is False
        assert updated["template_id"] is None

        delete_response = client.delete(
            f"/api/v1/projects/{project_id}",
            headers=_auth_headers(owner_id),
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted_at"] is not None

        hidden_response = client.get(
            f"/api/v1/projects/{project_id}",
            headers=_auth_headers(owner_id),
        )
        assert hidden_response.status_code == 404
        assert hidden_response.json()["code"] == "not_found"

        check_response = client.post(
            f"/api/v1/projects/{project_id}/setting/complete-check",
            headers=_auth_headers(owner_id),
        )
        assert check_response.status_code == 404
        assert check_response.json()["code"] == "not_found"

        trash_response = client.get(
            "/api/v1/projects",
            params={"deleted_only": "true"},
            headers=_auth_headers(owner_id),
        )
        assert trash_response.status_code == 200
        trashed = trash_response.json()
        assert len(trashed) == 1
        assert trashed[0]["id"] == project_id

        restore_response = client.post(
            f"/api/v1/projects/{project_id}/restore",
            headers=_auth_headers(owner_id),
        )
        assert restore_response.status_code == 200
        assert restore_response.json()["deleted_at"] is None

        restored_detail = client.get(
            f"/api/v1/projects/{project_id}",
            headers=_auth_headers(owner_id),
        )
        assert restored_detail.status_code == 200
        assert restored_detail.json()["name"] == "接口项目-更新"
    finally:
        client.close()
        engine.dispose()


def test_project_api_hides_other_users_project(monkeypatch) -> None:
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
            f"/api/v1/projects/{project_id}",
            headers=_auth_headers(outsider_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()
