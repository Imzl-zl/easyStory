from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.config_registry import ConfigLoader
from app.modules.context.service import ContextPreviewRequestDTO, create_context_preview_service
from app.modules.content.models import Content, ContentVersion
from app.modules.workflow.models import ChapterTask
from app.modules.workflow.service.snapshot_support import (
    dump_config,
    freeze_agents,
    freeze_skills,
    freeze_workflow,
)
from app.shared.runtime.errors import BusinessRuleError, NotFoundError
from tests.unit.models.helpers import create_project, create_user, create_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


def test_context_preview_service_returns_runtime_aligned_variables_and_report(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner)
    service = create_context_preview_service()

    preview = service.preview_workflow_context(
        db,
        workflow.id,
        ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
        owner_id=owner.id,
    )

    assert preview.node_id == "chapter_gen"
    assert preview.skill_id == "skill.chapter.xuanhuan"
    assert preview.model_name == "claude-sonnet-4-20250514"
    assert preview.variables["outline"] == "故事大纲"
    assert preview.variables["opening_plan"] == "前三章节奏规划"
    assert "主角初登场" in preview.variables["chapter_task"]
    statuses = {item["type"]: item["status"] for item in preview.context_report["sections"]}
    assert statuses["previous_chapters"] == "not_applicable"
    assert statuses["story_bible"] == "not_applicable"


def test_context_preview_service_requires_chapter_number_when_rules_need_it(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner)
    service = create_context_preview_service()

    with pytest.raises(BusinessRuleError, match="chapter_number"):
        service.preview_workflow_context(
            db,
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen"),
            owner_id=owner.id,
        )


def test_context_preview_service_hides_other_users_workflow(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner)
    service = create_context_preview_service()

    with pytest.raises(NotFoundError):
        service.preview_workflow_context(
            db,
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
            owner_id=outsider.id,
        )


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
