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
    ProjectDocumentRevisionStore,
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
) -> tuple[FastAPI, ProjectDocumentFileStore, ProjectDocumentIdentityStore]:
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
    return app, file_store, identity_store


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
) -> tuple[object, FastAPI, ProjectDocumentFileStore, ProjectDocumentIdentityStore, object, object, object]:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name=name)
    )
    app, file_store, identity_store = _build_project_document_app(
        async_session_factory=async_session_factory,
        document_root=tmp_path / "project-documents",
    )
    return session_factory, app, file_store, identity_store, engine, async_engine, database_path


def _create_owner_project(session_factory) -> tuple[object, object]:
    with session_factory() as session:
        owner = create_user(session)
        project = create_project(session, owner=owner, project_setting=ready_project_setting())
        return owner.id, project.id


def _collect_tree_paths(nodes: list[dict[str, object]]) -> tuple[str, ...]:
    collected: list[str] = []
    for node in nodes:
        collected.append(str(node["path"]))
        children = node.get("children")
        if isinstance(children, list):
            collected.extend(_collect_tree_paths(children))
    return tuple(collected)


async def test_project_api_save_project_document_uses_capability_write_chain(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-document-api-save")
    )
    app, file_store, identity_store = _build_project_document_app(
        async_session_factory=async_session_factory,
        document_root=tmp_path / "project-documents",
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner, project_setting=ready_project_setting())
            owner_id = owner.id
            project_id = project.id
        file_store.save_project_document(project_id, "设定/人物.md", "# 人物\n\n林渊")

        async with _started_project_document_client(app) as client:
            response = await client.put(
                f"/api/v1/projects/{project_id}/documents",
                params={"path": "设定/人物.md"},
                json={
                    "base_version": build_project_file_document_version("# 人物\n\n林渊"),
                    "content": "# 人物\n\n林渊\n\n新增：谨慎、克制。",
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "file"
        assert body["version"] == build_project_file_document_version(
            "# 人物\n\n林渊\n\n新增：谨慎、克制。"
        )
        assert isinstance(body["document_revision_id"], str) and body["document_revision_id"]
        assert isinstance(body["run_audit_id"], str) and body["run_audit_id"].startswith(
            "project_manual_save:"
        )
        identities = identity_store.list_document_identities(project_id)
        document_ref = next(item.document_ref for item in identities if item.path == "设定/人物.md")
        revisions = ProjectDocumentRevisionStore(file_store.root).list_revisions(
            project_id,
            document_ref=document_ref,
        )
        assert len(revisions) == 1
        assert revisions[0].document_revision_id == body["document_revision_id"]
        assert revisions[0].run_audit_id == body["run_audit_id"]
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_save_project_document_rejects_invalid_schema_bound_json(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-document-api-schema")
    )
    app, file_store, _ = _build_project_document_app(
        async_session_factory=async_session_factory,
        document_root=tmp_path / "project-documents",
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner, project_setting=ready_project_setting())
            owner_id = owner.id
            project_id = project.id
        file_store.save_project_document(project_id, "数据层/人物.json", '{\n  "characters": []\n}')

        async with _started_project_document_client(app) as client:
            response = await client.put(
                f"/api/v1/projects/{project_id}/documents",
                params={"path": "数据层/人物.json"},
                json={
                    "base_version": build_project_file_document_version('{\n  "characters": []\n}'),
                    "content": '{"characters":[{}]}',
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json() == {
            "code": "schema_validation_failed",
            "detail": "目标数据文稿 characters[0].id 必须是非空字符串。",
        }
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_get_project_document_returns_null_write_metadata(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-document-api-read")
    )
    app, file_store, _ = _build_project_document_app(
        async_session_factory=async_session_factory,
        document_root=tmp_path / "project-documents",
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner, project_setting=ready_project_setting())
            owner_id = owner.id
            project_id = project.id
        file_store.save_project_document(project_id, "附录/灵感碎片.md", "# 灵感\n\n雨夜追逐。")

        async with _started_project_document_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/documents",
                params={"path": "附录/灵感碎片.md"},
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        assert response.json()["document_revision_id"] is None
        assert response.json()["run_audit_id"] is None
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_list_document_catalog_returns_canonical_and_file_entries(
    monkeypatch,
    tmp_path,
) -> None:
    session_factory, app, file_store, _identity_store, engine, async_engine, database_path = (
        _build_project_document_test_runtime(
            monkeypatch,
            tmp_path,
            name="project-document-api-catalog",
        )
    )

    try:
        owner_id, project_id = _create_owner_project(session_factory)
        file_store.save_project_document(project_id, "设定/人物.md", "# 人物\n\n林渊")

        async with _started_project_document_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/document-catalog",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        catalog = response.json()
        assert catalog
        shared_catalog_version = catalog[0]["catalog_version"]
        assert all(item["catalog_version"] == shared_catalog_version for item in catalog)
        outline_entry = next(item for item in catalog if item["path"] == "大纲/总大纲.md")
        file_entry = next(item for item in catalog if item["path"] == "设定/人物.md")

        assert outline_entry["document_ref"] == "canonical:outline"
        assert outline_entry["source"] == "outline"
        assert outline_entry["version"].startswith("canonical:outline:")
        assert file_entry["source"] == "file"
        assert file_entry["writable"] is True
        assert file_entry["document_ref"].startswith("project_file:")
        assert file_entry["version"] == build_project_file_document_version("# 人物\n\n林渊")
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_save_project_document_rejects_version_conflict(
    monkeypatch,
    tmp_path,
) -> None:
    session_factory, app, file_store, _identity_store, engine, async_engine, database_path = (
        _build_project_document_test_runtime(
            monkeypatch,
            tmp_path,
            name="project-document-api-version-conflict",
        )
    )

    try:
        owner_id, project_id = _create_owner_project(session_factory)
        original_content = "# 人物\n\n林渊"
        file_store.save_project_document(project_id, "设定/人物.md", original_content)

        async with _started_project_document_client(app) as client:
            response = await client.put(
                f"/api/v1/projects/{project_id}/documents",
                params={"path": "设定/人物.md"},
                json={
                    "base_version": build_project_file_document_version(""),
                    "content": "# 人物\n\n林渊\n\n新增：当前版本已经过时。",
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json() == {
            "code": "version_conflict",
            "detail": "目标文稿版本已变化，请重新读取最新内容后再写入。",
        }
        persisted = file_store.find_project_document(project_id, "设定/人物.md")
        assert persisted is not None
        assert persisted.content == original_content
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_document_entry_crud_round_trip_updates_tree_and_catalog(
    monkeypatch,
    tmp_path,
) -> None:
    session_factory, app, _file_store, identity_store, engine, async_engine, database_path = (
        _build_project_document_test_runtime(
            monkeypatch,
            tmp_path,
            name="project-document-api-entry-crud",
        )
    )

    try:
        owner_id, project_id = _create_owner_project(session_factory)
        folder_path = "附录/补充"
        source_file_path = "附录/补充/线索汇总.md"
        target_file_path = "附录/补充/线索总表.md"

        async with _started_project_document_client(app) as client:
            create_folder_response = await client.post(
                f"/api/v1/projects/{project_id}/document-files",
                json={"kind": "folder", "path": folder_path},
                headers=_auth_headers(owner_id),
            )
            create_file_response = await client.post(
                f"/api/v1/projects/{project_id}/document-files",
                json={"kind": "file", "path": source_file_path},
                headers=_auth_headers(owner_id),
            )
            tree_response = await client.get(
                f"/api/v1/projects/{project_id}/document-files/tree",
                headers=_auth_headers(owner_id),
            )
            catalog_response = await client.get(
                f"/api/v1/projects/{project_id}/document-catalog",
                headers=_auth_headers(owner_id),
            )
            rename_response = await client.patch(
                f"/api/v1/projects/{project_id}/document-files/rename",
                json={"path": source_file_path, "next_path": target_file_path},
                headers=_auth_headers(owner_id),
            )
            catalog_after_rename_response = await client.get(
                f"/api/v1/projects/{project_id}/document-catalog",
                headers=_auth_headers(owner_id),
            )
            delete_file_response = await client.delete(
                f"/api/v1/projects/{project_id}/document-files",
                params={"path": target_file_path},
                headers=_auth_headers(owner_id),
            )
            delete_folder_response = await client.delete(
                f"/api/v1/projects/{project_id}/document-files",
                params={"path": folder_path},
                headers=_auth_headers(owner_id),
            )
            tree_after_cleanup_response = await client.get(
                f"/api/v1/projects/{project_id}/document-files/tree",
                headers=_auth_headers(owner_id),
            )
            catalog_after_cleanup_response = await client.get(
                f"/api/v1/projects/{project_id}/document-catalog",
                headers=_auth_headers(owner_id),
            )

        assert create_folder_response.status_code == 201
        assert create_folder_response.json()["path"] == folder_path
        assert create_file_response.status_code == 201
        assert create_file_response.json()["path"] == source_file_path

        tree_paths = _collect_tree_paths(tree_response.json())
        assert folder_path in tree_paths
        assert source_file_path in tree_paths

        catalog_entry = next(
            item for item in catalog_response.json() if item["path"] == source_file_path
        )
        assert catalog_entry["document_ref"].startswith("project_file:")
        original_document_ref = catalog_entry["document_ref"]

        assert rename_response.status_code == 200
        assert rename_response.json()["path"] == target_file_path
        catalog_after_rename = catalog_after_rename_response.json()
        renamed_entry = next(
            item for item in catalog_after_rename if item["path"] == target_file_path
        )
        assert renamed_entry["document_ref"] == original_document_ref
        assert not any(item["path"] == source_file_path for item in catalog_after_rename)

        assert delete_file_response.status_code == 200
        assert delete_file_response.json() == {
            "node_type": "file",
            "path": target_file_path,
        }
        assert delete_folder_response.status_code == 200
        assert delete_folder_response.json() == {
            "node_type": "folder",
            "path": folder_path,
        }

        tree_paths_after_cleanup = _collect_tree_paths(tree_after_cleanup_response.json())
        assert folder_path not in tree_paths_after_cleanup
        assert target_file_path not in tree_paths_after_cleanup
        assert not any(
            item["path"] == target_file_path
            for item in catalog_after_cleanup_response.json()
        )
        identities = identity_store.list_document_identities(project_id)
        assert not any(item.path.startswith(folder_path) for item in identities)
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
