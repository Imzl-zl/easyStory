from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import ContextInjectionItem
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
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user, create_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


def test_context_preview_service_returns_runtime_aligned_variables_and_report(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner)
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
            owner_id=owner.id,
        )
    )

    assert preview.node_id == "chapter_gen"
    assert preview.skill_id == "skill.chapter.xuanhuan"
    assert preview.model_name == "claude-sonnet-4-20250514"
    assert preview.variables["outline"] == "故事大纲"
    assert preview.variables["opening_plan"] == "前三章节奏规划"
    assert "主角初登场" in preview.variables["chapter_task"]
    assert "故事大纲" in preview.rendered_prompt
    assert "前三章节奏规划" in preview.rendered_prompt
    statuses = {item["type"]: item["status"] for item in preview.context_report["sections"]}
    assert statuses["previous_chapters"] == "not_applicable"
    assert statuses["story_bible"] == "not_applicable"


def test_context_preview_service_requires_chapter_number_when_rules_need_it(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner)
    service = create_context_preview_service()

    with pytest.raises(BusinessRuleError, match="chapter_number"):
        asyncio.run(
            service.preview_workflow_context(
                async_db(db),
                workflow.id,
                ContextPreviewRequestDTO(node_id="chapter_gen"),
                owner_id=owner.id,
            )
        )


def test_context_preview_service_auto_injects_setting_projections_for_opening_plan(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner)
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(node_id="opening_plan"),
            owner_id=owner.id,
        )
    )

    assert "world_setting" in preview.variables
    assert "character_profile" in preview.variables
    assert "时代基线：宗门时代" in preview.variables["world_setting"]
    assert "[主角]" in preview.variables["character_profile"]
    assert "林渊" in preview.variables["character_profile"]
    assert "苏晚" in preview.variables["character_profile"]
    assert "时代基线：宗门时代" in preview.rendered_prompt
    assert "[主角]" in preview.rendered_prompt
    statuses = {item["type"]: item["status"] for item in preview.context_report["sections"]}
    assert statuses["world_setting"] == "included"
    assert statuses["character_profile"] == "included"


def test_context_preview_service_accepts_request_level_character_profile_for_chapter_skill(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(
        db,
        owner=owner,
        include_chapter_character_profile_prompt=True,
    )
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(
                node_id="chapter_gen",
                chapter_number=1,
                extra_inject=[ContextInjectionItem.model_validate({"type": "character_profile"})],
            ),
            owner_id=owner.id,
        )
    )

    assert "character_profile" in preview.variables
    assert "[主角]" in preview.variables["character_profile"]
    assert "林渊" in preview.variables["character_profile"]
    assert "苏晚" in preview.variables["character_profile"]
    statuses = {item["type"]: item["status"] for item in preview.context_report["sections"]}
    assert statuses["character_profile"] == "included"


def test_context_preview_service_supports_request_level_chapter_summary(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(
        db,
        owner=owner,
        include_chapter_summary_prompt=True,
    )
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
            ContextPreviewRequestDTO(
                node_id="outline",
                chapter_number=3,
                extra_inject=[ContextInjectionItem.model_validate({"type": "chapter_summary", "count": 2})],
            ),
            owner_id=owner.id,
        )
    )

    assert "chapter_summary" in preview.variables
    assert "第1章 第一章 初入宗门" in preview.variables["chapter_summary"]
    assert "摘要：" in preview.rendered_prompt
    section = next(item for item in preview.context_report["sections"] if item["type"] == "chapter_summary")
    assert section["status"] == "included"
    assert section["chapters"] == [1, 2]
    assert section["summary_mode"] == "current_version_excerpt"


def test_context_preview_service_hides_other_users_workflow(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner)
    service = create_context_preview_service()

    with pytest.raises(NotFoundError):
        asyncio.run(
            service.preview_workflow_context(
                async_db(db),
                workflow.id,
                ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
                owner_id=outsider.id,
            )
        )


def _create_preview_workflow(
    db,
    *,
    owner,
    include_chapter_summary_prompt: bool = False,
    include_chapter_character_profile_prompt: bool = False,
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
    if include_chapter_summary_prompt:
        skills_snapshot["skill.outline.xuanhuan"]["prompt"] += "\n{% if chapter_summary %}\n{{ chapter_summary }}\n{% endif %}"
    if include_chapter_character_profile_prompt:
        skills_snapshot["skill.chapter.xuanhuan"]["prompt"] += (
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
