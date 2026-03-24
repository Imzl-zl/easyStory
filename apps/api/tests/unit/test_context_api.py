from __future__ import annotations

from pathlib import Path

from app.main import create_app
from app.modules.analysis.models import Analysis
from app.modules.config_registry import ConfigLoader
from app.modules.content.models import Content, ContentVersion
from app.modules.workflow.models import ChapterTask
from app.modules.workflow.service.snapshot_support import (
    dump_config,
    freeze_agents,
    freeze_skills,
    freeze_workflow,
)
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_project, create_user, create_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


async def test_context_api_previews_workflow_node_context(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-preview")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(session, owner=owner)
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={"node_id": "chapter_gen", "chapter_number": 1},
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["node_id"] == "chapter_gen"
        assert body["skill_id"] == "skill.chapter.xuanhuan"
        assert body["variables"]["outline"] == "故事大纲"
        assert "故事大纲" in body["rendered_prompt"]
        statuses = {item["type"]: item["status"] for item in body["context_report"]["sections"]}
        assert statuses["previous_chapters"] == "not_applicable"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_context_api_rejects_preview_without_required_chapter_number(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-validation")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(session, owner=owner)
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={"node_id": "chapter_gen"},
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_context_api_accepts_request_level_style_reference(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-style-reference")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(
                session,
                owner=owner,
                include_style_reference_prompt=True,
            )
            analysis = Analysis(
                project_id=workflow.project_id,
                analysis_type="style",
                source_title="请求级参考",
                result={"writing_style": {"rhythm": "floating"}},
            )
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={
                    "node_id": "chapter_gen",
                    "chapter_number": 1,
                    "extra_inject": [
                        {
                            "type": "style_reference",
                            "analysis_id": str(analysis.id),
                            "inject_fields": ["writing_style"],
                        }
                    ],
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert "style_reference" in body["variables"]
        assert "请求级参考" in body["variables"]["style_reference"]
        assert "请求级参考" in body["rendered_prompt"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_context_api_accepts_request_level_character_profile(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-character-profile")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(
                session,
                owner=owner,
                include_opening_plan_character_profile_prompt=True,
            )
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={
                    "node_id": "opening_plan",
                    "extra_inject": [{"type": "character_profile"}],
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert "character_profile" in body["variables"]
        assert "林渊" in body["variables"]["character_profile"]
        assert "苏晚" in body["variables"]["character_profile"]
        section = next(item for item in body["context_report"]["sections"] if item["type"] == "character_profile")
        assert section["status"] == "included"
        assert section["supporting_roles_count"] == 1
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_context_api_accepts_request_level_chapter_summary(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-chapter-summary")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(
                session,
                owner=owner,
                include_chapter_summary_prompt=True,
            )
            _create_content_with_version(
                session,
                workflow.project_id,
                "chapter",
                "第一章 初入宗门",
                "林渊第一次踏入山门，看见云海翻涌，也第一次意识到九州大陆的修行秩序比想象中更残酷。",
                chapter_number=1,
            )
            _create_content_with_version(
                session,
                workflow.project_id,
                "chapter",
                "第二章 山门试炼",
                "外门试炼开始后，林渊在石阶尽头遇见旧敌，勉强守住名额，也记下了宗门内部复杂的派系关系。",
                chapter_number=2,
            )
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={
                    "node_id": "outline",
                    "chapter_number": 3,
                    "extra_inject": [{"type": "chapter_summary", "count": 2}],
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert "chapter_summary" in body["variables"]
        assert "第1章 第一章 初入宗门" in body["variables"]["chapter_summary"]
        section = next(item for item in body["context_report"]["sections"] if item["type"] == "chapter_summary")
        assert section["status"] == "included"
        assert section["chapters"] == [1, 2]
        assert section["summary_mode"] == "current_version_excerpt"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_context_api_rejects_missing_analysis_for_request_level_style_reference(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-style-reference-missing")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(
                session,
                owner=owner,
                include_style_reference_prompt=True,
            )
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={
                    "node_id": "chapter_gen",
                    "chapter_number": 1,
                    "extra_inject": [
                        {
                            "type": "style_reference",
                            "analysis_id": "00000000-0000-0000-0000-000000000001",
                            "inject_fields": ["writing_style"],
                        }
                    ],
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_context_api_hides_other_users_workflow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-owner")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(session, owner=owner)
            outsider = create_user(session)
            workflow_id = workflow.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={"node_id": "chapter_gen", "chapter_number": 1},
                headers=_auth_headers(outsider_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _create_preview_workflow(
    db,
    *,
    owner,
    include_style_reference_prompt: bool = False,
    include_chapter_summary_prompt: bool = False,
    include_opening_plan_character_profile_prompt: bool = False,
    task_chapter_number: int = 1,
):
    project = create_project(
        db,
        owner=owner,
        project_setting={
            "genre": "玄幻",
            "protagonist": {"name": "林渊", "goal": "进入宗门"},
            "key_supporting_roles": [{"name": "苏晚", "identity": "药师", "goal": "查清师门旧案"}],
            "world_setting": {"era_baseline": "宗门时代"},
        },
    )
    config_loader = ConfigLoader(CONFIG_ROOT)
    workflow_config = config_loader.load_workflow("workflow.xuanhuan_manual")
    agents = freeze_agents(config_loader, workflow_config)
    skills_snapshot = freeze_skills(config_loader, workflow_config, agents)
    if include_style_reference_prompt:
        skills_snapshot["skill.chapter.xuanhuan"]["prompt"] += "\n{{ style_reference }}"
    if include_chapter_summary_prompt:
        skills_snapshot["skill.outline.xuanhuan"]["prompt"] += "\n{% if chapter_summary %}\n{{ chapter_summary }}\n{% endif %}"
    if include_opening_plan_character_profile_prompt:
        skills_snapshot["skill.opening_plan.xuanhuan"]["prompt"] += (
            "\n{% if character_profile %}\n【人物设定】\n{{ character_profile }}\n{% endif %}"
        )
    workflow = create_workflow(
        db,
        project=project,
        status="running",
        current_node_id="chapter_gen",
        workflow_snapshot=freeze_workflow(config_loader, workflow_config),
        skills_snapshot=skills_snapshot,
        agents_snapshot={agent.id: dump_config(agent) for agent in agents},
    )
    _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=task_chapter_number,
            title=f"第{task_chapter_number}章",
            brief="主角初登场",
            key_characters=["林渊"],
            key_events=["进入宗门"],
        )
    )
    db.commit()
    db.refresh(workflow)
    return workflow


def _create_content_with_version(
    db,
    project_id,
    content_type: str,
    title: str,
    text: str,
    *,
    chapter_number: int | None = None,
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
        chapter_number=chapter_number,
        status="approved",
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=text,
            is_current=True,
        )
    )
    db.commit()
