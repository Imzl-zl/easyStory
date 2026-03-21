from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.modules.project.models import Project
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import (
    TEST_JWT_SECRET,
    auth_headers as _auth_headers,
    build_runtime_app as _build_runtime_app,
    seed_workflow_project as _seed_project,
)
from tests.unit.models.helpers import (
    create_chapter_task,
    create_content,
    create_content_version,
    create_user,
    create_workflow,
)


async def test_export_api_creates_lists_and_downloads_exports(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="export-api-success")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    workflow_id = _seed_exportable_workflow(session_factory, project_id)
    export_root = _build_export_root()
    app = _build_runtime_app(
        session_factory,
        async_session_factory,
        export_root=export_root,
    )
    headers = _auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            create_response = await client.post(
                f"/api/v1/workflows/{workflow_id}/exports",
                json={"formats": ["txt"]},
                headers=headers,
            )
            assert create_response.status_code == 200
            created_exports = create_response.json()
            assert len(created_exports) == 1
            export_id = created_exports[0]["id"]

            list_response = await client.get(
                f"/api/v1/projects/{project_id}/exports",
                headers=headers,
            )
            assert list_response.status_code == 200
            listed_ids = [item["id"] for item in list_response.json()]
            assert export_id in listed_ids

            download_response = await client.get(
                f"/api/v1/exports/{export_id}/download",
                headers=headers,
            )

        assert download_response.status_code == 200
        assert "第一章导出正文" in download_response.text
        assert list(export_root.rglob("*.txt"))
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
        shutil.rmtree(export_root, ignore_errors=True)


async def test_export_download_hides_other_users_export(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="export-api-owner")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    workflow_id = _seed_exportable_workflow(session_factory, project_id)
    export_root = _build_export_root()
    app = _build_runtime_app(
        session_factory,
        async_session_factory,
        export_root=export_root,
    )
    owner_headers = _auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            create_response = await client.post(
                f"/api/v1/workflows/{workflow_id}/exports",
                json={"formats": ["txt"]},
                headers=owner_headers,
            )
            export_id = create_response.json()[0]["id"]

            with session_factory() as session:
                outsider_headers = _auth_headers(create_user(session).id)

            response = await client.get(
                f"/api/v1/exports/{export_id}/download",
                headers=outsider_headers,
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
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
