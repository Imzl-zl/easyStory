from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
import httpx

from app.main import create_app
from app.modules.project.entry.http.router import (
    get_project_document_capability_service,
    get_project_service,
)
from app.modules.project.infrastructure import (
    ProjectDocumentFileStore,
    ProjectDocumentIdentityStore,
)
from app.modules.project.service import (
    ProjectDocumentCapabilityService,
    ProjectService,
)
from app.modules.project.service.project_document_version_support import (
    build_project_file_document_version,
)
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_project, create_user, ready_project_setting


def _build_project_document_app(
    *,
    async_session_factory,
    document_root,
) -> FastAPI:
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    app = create_app(async_session_factory=async_session_factory)
    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_project_document_capability_service] = (
        lambda: capability_service
    )
    return app


@asynccontextmanager
async def _started_project_document_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


def _build_project_document_test_runtime(
    monkeypatch,
    tmp_path,
    *,
    name: str,
) -> tuple[object, FastAPI, object, object, object]:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name=name)
    )
    app = _build_project_document_app(
        async_session_factory=async_session_factory,
        document_root=tmp_path / "project-documents",
    )
    return session_factory, app, engine, async_engine, database_path


def _create_owner_project(session_factory) -> tuple[object, object]:
    with session_factory() as session:
        owner = create_user(session)
        project = create_project(session, owner=owner, project_setting=ready_project_setting())
        return owner.id, project.id


async def test_project_api_save_project_document_rejects_non_document_path_as_not_found(
    monkeypatch,
    tmp_path,
) -> None:
    session_factory, app, engine, async_engine, database_path = (
        _build_project_document_test_runtime(
            monkeypatch,
            tmp_path,
            name="project-document-api-error-save-directory",
        )
    )

    try:
        owner_id, project_id = _create_owner_project(session_factory)

        async with _started_project_document_client(app) as client:
            response = await client.put(
                f"/api/v1/projects/{project_id}/documents",
                params={"path": "设定"},
                json={
                    "base_version": build_project_file_document_version(""),
                    "content": "# 不应写入目录",
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json() == {
            "code": "document_not_found",
            "detail": "目标文稿不存在于当前项目目录，无法写回。",
        }
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_create_document_entry_rejects_non_chapter_file_under_content_root(
    monkeypatch,
    tmp_path,
) -> None:
    session_factory, app, engine, async_engine, database_path = (
        _build_project_document_test_runtime(
            monkeypatch,
            tmp_path,
            name="project-document-api-error-create-content-file",
        )
    )

    try:
        owner_id, project_id = _create_owner_project(session_factory)

        async with _started_project_document_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/document-files",
                json={"kind": "file", "path": "正文/临时笔记.md"},
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json() == {
            "code": "business_rule_error",
            "detail": "正文下只能新建章节文稿，其他区域只能新建自定义 .md 或 .json 文稿",
        }
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_delete_document_entry_rejects_fixed_slot_root(
    monkeypatch,
    tmp_path,
) -> None:
    session_factory, app, engine, async_engine, database_path = (
        _build_project_document_test_runtime(
            monkeypatch,
            tmp_path,
            name="project-document-api-error-delete-fixed-root",
        )
    )

    try:
        owner_id, project_id = _create_owner_project(session_factory)

        async with _started_project_document_client(app) as client:
            response = await client.delete(
                f"/api/v1/projects/{project_id}/document-files",
                params={"path": "设定"},
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json() == {
            "code": "business_rule_error",
            "detail": "固定目录不支持删除",
        }
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
