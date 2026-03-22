from __future__ import annotations

from app.modules.project.models import Project
from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import (
    create_chapter_task,
    create_content,
    create_content_version,
    create_project,
    create_template,
    create_user,
    create_workflow,
    ready_project_setting,
)


async def test_project_api_manages_project_lifecycle(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-api-lifecycle")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            template = create_template(session)
            owner_id = owner.id
            template_id = template.id

        async with started_async_client(app) as client:
            create_response = await client.post(
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

            outline_response = await client.get(
                f"/api/v1/projects/{project_id}/outline",
                headers=_auth_headers(owner_id),
            )
            opening_plan_response = await client.get(
                f"/api/v1/projects/{project_id}/opening-plan",
                headers=_auth_headers(owner_id),
            )
            assert outline_response.status_code == 200
            assert outline_response.json()["title"] == "大纲"
            assert outline_response.json()["status"] == "draft"
            assert outline_response.json()["version_number"] == 1
            assert outline_response.json()["content_text"] == ""
            assert opening_plan_response.status_code == 200
            assert opening_plan_response.json()["title"] == "开篇设计"
            assert opening_plan_response.json()["status"] == "draft"
            assert opening_plan_response.json()["version_number"] == 1
            assert opening_plan_response.json()["content_text"] == ""

            list_response = await client.get("/api/v1/projects", headers=_auth_headers(owner_id))
            assert list_response.status_code == 200
            listed = list_response.json()
            assert len(listed) == 1
            assert listed[0]["id"] == project_id

            detail_response = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 200
            assert detail_response.json()["name"] == "接口项目"

            update_response = await client.put(
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

            delete_response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(owner_id),
            )
            assert delete_response.status_code == 200
            assert delete_response.json()["deleted_at"] is not None

            hidden_response = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(owner_id),
            )
            assert hidden_response.status_code == 404
            assert hidden_response.json()["code"] == "not_found"

            check_response = await client.post(
                f"/api/v1/projects/{project_id}/setting/complete-check",
                headers=_auth_headers(owner_id),
            )
            assert check_response.status_code == 404
            assert check_response.json()["code"] == "not_found"

            trash_response = await client.get(
                "/api/v1/projects",
                params={"deleted_only": "true"},
                headers=_auth_headers(owner_id),
            )
            assert trash_response.status_code == 200
            trashed = trash_response.json()
            assert len(trashed) == 1
            assert trashed[0]["id"] == project_id

            restore_response = await client.post(
                f"/api/v1/projects/{project_id}/restore",
                headers=_auth_headers(owner_id),
            )
            assert restore_response.status_code == 200
            assert restore_response.json()["deleted_at"] is None

            restored_detail = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(owner_id),
            )
            assert restored_detail.status_code == 200
            assert restored_detail.json()["name"] == "接口项目-更新"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_setting_update_api_returns_impact_summary(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-api-setting-impact")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(
                session,
                owner=owner,
                project_setting=ready_project_setting(),
            )
            workflow = create_workflow(session, project=project, status="paused")
            outline = create_content(
                session,
                project=project,
                content_type="outline",
                title="大纲",
                chapter_number=None,
            )
            outline.status = "approved"
            opening_plan = create_content(
                session,
                project=project,
                content_type="opening_plan",
                title="开篇设计",
                chapter_number=None,
            )
            opening_plan.status = "approved"
            chapter = create_content(session, project=project, title="第一章")
            chapter.status = "approved"
            create_content_version(session, content=outline, content_text="旧大纲", version_number=1)
            create_content_version(
                session,
                content=opening_plan,
                content_text="旧开篇",
                version_number=1,
            )
            create_chapter_task(
                session,
                workflow=workflow,
                chapter_number=1,
                title="第一章",
                brief="旧章节计划",
                status="pending",
            )
            session.commit()
            owner_id = owner.id
            project_id = project.id

        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/projects/{project_id}/setting",
                json={
                    "project_setting": {
                        "genre": "仙侠",
                        "tone": "冷峻",
                        "core_conflict": "主角在宗门追杀中求生",
                        "protagonist": {
                            "name": "林渊",
                            "identity": "弃徒",
                            "goal": "重返内门",
                        },
                        "world_setting": {
                            "era_baseline": "宗门割据时代",
                            "world_rules": "境界压制",
                        },
                    }
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["genre"] == "仙侠"
        assert body["impact"]["has_impact"] is True
        assert body["impact"]["total_affected_entries"] == 4
        assert [(item["target"], item["count"]) for item in body["impact"]["items"]] == [
            ("outline", 1),
            ("opening_plan", 1),
            ("chapter", 1),
            ("chapter_tasks", 1),
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_rejects_physical_delete_before_soft_delete(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-api-physical-guard")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            owner_id = owner.id
            project_id = project.id

        async with started_async_client(app) as client:
            response = await client.delete(
                f"/api/v1/projects/{project_id}/physical",
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 422
            assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_api_physically_deletes_soft_deleted_project(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-api-physical-delete")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            owner_id = owner.id
            project_id = project.id

        async with started_async_client(app) as client:
            soft_delete_response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(owner_id),
            )
            assert soft_delete_response.status_code == 200

            physical_delete_response = await client.delete(
                f"/api/v1/projects/{project_id}/physical",
                headers=_auth_headers(owner_id),
            )
            assert physical_delete_response.status_code == 204

            detail_response = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 404

        with session_factory() as session:
            assert session.get(Project, project_id) is None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
async def test_project_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-api-owner")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(outsider_id),
            )
            assert response.status_code == 404
            assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
