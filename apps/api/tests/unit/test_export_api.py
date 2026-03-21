from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.modules.project.models import Project
from tests.unit.models.helpers import (
    create_chapter_task,
    create_content,
    create_content_version,
    create_user,
    create_workflow,
)
from tests.unit.test_workflow_api import (
    _auth_headers,
    _build_runtime_client,
    _build_session_factory,
    _seed_project,
)

TEST_JWT_SECRET = "test-jwt-secret"


def test_export_api_creates_lists_and_downloads_exports(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    workflow_id = _seed_exportable_workflow(session_factory, project_id)
    export_root = _build_export_root()
    client = _build_runtime_client(session_factory, export_root=export_root)
    headers = _auth_headers(owner_id)

    try:
        create_response = client.post(
            f"/api/v1/workflows/{workflow_id}/exports",
            json={"formats": ["txt"]},
            headers=headers,
        )
        assert create_response.status_code == 200
        created_exports = create_response.json()
        assert len(created_exports) == 1
        export_id = created_exports[0]["id"]

        list_response = client.get(
            f"/api/v1/projects/{project_id}/exports",
            headers=headers,
        )
        assert list_response.status_code == 200
        listed_ids = [item["id"] for item in list_response.json()]
        assert export_id in listed_ids

        download_response = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers=headers,
        )
        assert download_response.status_code == 200
        assert "第一章导出正文" in download_response.text
        assert list(export_root.rglob("*.txt"))
    finally:
        client.close()
        engine.dispose()
        shutil.rmtree(export_root, ignore_errors=True)


def test_export_download_hides_other_users_export(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    workflow_id = _seed_exportable_workflow(session_factory, project_id)
    export_root = _build_export_root()
    client = _build_runtime_client(session_factory, export_root=export_root)
    owner_headers = _auth_headers(owner_id)

    try:
        create_response = client.post(
            f"/api/v1/workflows/{workflow_id}/exports",
            json={"formats": ["txt"]},
            headers=owner_headers,
        )
        export_id = create_response.json()[0]["id"]

        with session_factory() as session:
            outsider_headers = _auth_headers(create_user(session).id)

        response = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers=outsider_headers,
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()
        shutil.rmtree(export_root, ignore_errors=True)


def _seed_exportable_workflow(
    session_factory,
    project_id: str,
) -> str:
    with session_factory() as session:
        project = session.get(Project, uuid.UUID(project_id))
        assert project is not None
        workflow = create_workflow(
            session,
            project=project,
            template_id=project.template_id,
            status="paused",
        )
        chapter = create_content(
            session,
            project=project,
            chapter_number=1,
            title="第一章",
            status="approved",
        )
        create_content_version(
            session,
            content=chapter,
            version_number=1,
            content_text="第一章导出正文",
            is_current=True,
        )
        create_chapter_task(
            session,
            workflow=workflow,
            chapter_number=1,
            status="completed",
            content_id=chapter.id,
        )
        return str(workflow.id)


def _build_export_root() -> Path:
    return Path.cwd() / ".pytest-exports" / f"export-api-{uuid.uuid4().hex}"
