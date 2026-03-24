from __future__ import annotations

from pathlib import Path

from app.main import create_app
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


async def test_context_api_reports_configuration_error_for_unconfigured_rendered_prompt(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-rendered-prompt-config")
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

        assert response.status_code == 500
        assert response.json()["code"] == "configuration_error"
        assert "style_reference" in response.json()["detail"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_context_api_auto_injects_setting_projections_for_outline_skill(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="context-api-outline-projections")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(session, owner=owner, include_style_reference_prompt=False)
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/context-preview",
                json={"node_id": "outline"},
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert "character_profile" in body["variables"]
        assert "world_setting" in body["variables"]
        assert "林渊" in body["variables"]["character_profile"]
        assert "时代基线：宗门时代" in body["variables"]["world_setting"]
        assert "林渊" in body["rendered_prompt"]
        assert "时代基线：宗门时代" in body["rendered_prompt"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _create_preview_workflow(db, *, owner, include_style_reference_prompt: bool = True):
    project = create_project(
        db,
        owner=owner,
        project_setting={
            "genre": "玄幻",
            "protagonist": {"name": "林渊", "goal": "进入宗门"},
            "world_setting": {"era_baseline": "宗门时代"},
        },
    )
    config_loader = ConfigLoader(CONFIG_ROOT)
    workflow_config = config_loader.load_workflow("workflow.xuanhuan_manual")
    agents = freeze_agents(config_loader, workflow_config)
    skills_snapshot = freeze_skills(config_loader, workflow_config, agents)
    if include_style_reference_prompt:
        skills_snapshot["skill.chapter.xuanhuan"]["prompt"] += "\n{{ style_reference }}"
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
            chapter_number=1,
            title="第一章",
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
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
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
