from __future__ import annotations

import asyncio
from pathlib import Path

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
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user, create_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


def test_chapter_skill_auto_injects_builtin_chapter_summary_for_later_chapter(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, task_chapter_number=3)
    _create_content_with_version(
        db,
        workflow.project_id,
        "chapter",
        "第一章 初入宗门",
        "林渊第一次踏入山门，看见云海翻涌，也第一次意识到九州大陆的修行秩序比想象中更残酷。",
        chapter_number=1,
    )
    _create_content_with_version(
        db,
        workflow.project_id,
        "chapter",
        "第二章 山门试炼",
        "外门试炼开始后，林渊在石阶尽头遇见旧敌，勉强守住名额，也记下了宗门内部复杂的派系关系。",
        chapter_number=2,
    )
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=3),
            owner_id=owner.id,
        )
    )

    assert "chapter_summary" in preview.variables
    assert "第1章 第一章 初入宗门" in preview.variables["chapter_summary"]
    assert "【近期摘要】" in preview.rendered_prompt
    section = next(item for item in preview.context_report["sections"] if item["type"] == "chapter_summary")
    assert section["status"] == "included"
    assert section["chapters"] == [1, 2]
    assert section["summary_mode"] == "current_version_excerpt"


def test_chapter_skill_marks_builtin_chapter_summary_not_applicable_for_first_chapter(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, task_chapter_number=1)
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
            owner_id=owner.id,
        )
    )

    assert preview.variables["chapter_summary"] == ""
    assert "【近期摘要】" not in preview.rendered_prompt
    section = next(item for item in preview.context_report["sections"] if item["type"] == "chapter_summary")
    assert section["status"] == "not_applicable"
    assert section["chapters"] == []


def _create_preview_workflow(
    db,
    *,
    owner,
    task_chapter_number: int,
):
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
