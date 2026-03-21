from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.content.models import Content, ContentVersion
from app.modules.workflow.models import ChapterTask
from app.modules.workflow.service.snapshot_support import (
    dump_config,
    freeze_agents,
    freeze_skills,
    freeze_workflow,
)
from tests.unit.models.helpers import create_project, create_user, create_workflow
from tests.unit.test_workflow_api import (
    TEST_JWT_SECRET,
    _auth_headers,
    _build_runtime_client,
    _build_session_factory,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


def test_context_api_previews_workflow_node_context(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = _build_runtime_client(session_factory)

    try:
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(session, owner=owner)
            workflow_id = workflow.id
            owner_id = owner.id

        response = client.post(
            f"/api/v1/workflows/{workflow_id}/context-preview",
            json={"node_id": "chapter_gen", "chapter_number": 1},
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["node_id"] == "chapter_gen"
        assert body["skill_id"] == "skill.chapter.xuanhuan"
        assert body["variables"]["outline"] == "故事大纲"
        statuses = {item["type"]: item["status"] for item in body["context_report"]["sections"]}
        assert statuses["previous_chapters"] == "not_applicable"
    finally:
        client.close()
        engine.dispose()


def test_context_api_rejects_preview_without_required_chapter_number(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = _build_runtime_client(session_factory)

    try:
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(session, owner=owner)
            workflow_id = workflow.id
            owner_id = owner.id

        response = client.post(
            f"/api/v1/workflows/{workflow_id}/context-preview",
            json={"node_id": "chapter_gen"},
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
    finally:
        client.close()
        engine.dispose()


def test_context_api_hides_other_users_workflow(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = _build_runtime_client(session_factory)

    try:
        with session_factory() as session:
            owner = create_user(session)
            workflow = _create_preview_workflow(session, owner=owner)
            outsider = create_user(session)
            workflow_id = workflow.id
            outsider_id = outsider.id

        response = client.post(
            f"/api/v1/workflows/{workflow_id}/context-preview",
            json={"node_id": "chapter_gen", "chapter_number": 1},
            headers=_auth_headers(outsider_id),
        )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()


def _create_preview_workflow(db, *, owner):
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
    workflow = create_workflow(
        db,
        project=project,
        status="running",
        current_node_id="chapter_gen",
        workflow_snapshot=freeze_workflow(config_loader, workflow_config),
        skills_snapshot=freeze_skills(config_loader, workflow_config, agents),
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
