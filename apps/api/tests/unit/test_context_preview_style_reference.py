from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.modules.analysis.models import Analysis
from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import ContextInjectionItem
from app.modules.content.models import Content, ContentVersion
from app.modules.context.service.dto import ContextPreviewRequestDTO
from app.modules.context.service.factory import create_context_preview_service
from app.modules.context.engine.errors import ContextBuilderError
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


def test_context_preview_service_includes_style_reference_when_explicitly_configured(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, inject_style_reference=True)
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
            owner_id=owner.id,
        )
    )

    assert "style_reference" in preview.variables
    assert "writing_style" in preview.variables["style_reference"]
    assert "writing_style" in preview.rendered_prompt
    statuses = {item["type"]: item["status"] for item in preview.context_report["sections"]}
    assert statuses["style_reference"] == "included"


def test_context_preview_service_skips_zero_config_auto_injection_for_style_reference(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(
        db,
        owner=owner,
        inject_style_reference=False,
        include_style_reference_prompt=False,
    )
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
            owner_id=owner.id,
        )
    )

    assert "style_reference" not in preview.variables
    statuses = {item["type"]: item["status"] for item in preview.context_report["sections"]}
    assert "style_reference" not in statuses


def test_context_preview_service_accepts_request_level_style_reference(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, inject_style_reference=False)
    analysis = Analysis(
        project_id=workflow.project_id,
        analysis_type="style",
        source_title="请求级参考",
        result={"writing_style": {"rhythm": "floating"}},
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(
                node_id="chapter_gen",
                chapter_number=1,
                extra_inject=[
                    {
                        "type": "style_reference",
                        "analysis_id": analysis.id,
                        "inject_fields": ["writing_style"],
                    }
                ],
            ),
            owner_id=owner.id,
        )
    )

    assert "style_reference" in preview.variables
    assert "请求级参考" in preview.variables["style_reference"]
    assert "请求级参考" in preview.rendered_prompt
    statuses = {item["type"]: item["status"] for item in preview.context_report["sections"]}
    assert statuses["style_reference"] == "included"


def test_context_preview_service_request_level_style_reference_overrides_snapshot(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, inject_style_reference=True)
    override_analysis = Analysis(
        project_id=workflow.project_id,
        analysis_type="style",
        source_title="覆盖参考",
        result={"writing_style": {"rhythm": "sharp"}},
    )
    db.add(override_analysis)
    db.commit()
    db.refresh(override_analysis)
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(
                node_id="chapter_gen",
                chapter_number=1,
                extra_inject=[
                    {
                        "type": "style_reference",
                        "analysis_id": override_analysis.id,
                        "inject_fields": ["writing_style"],
                    }
                ],
            ),
            owner_id=owner.id,
        )
    )

    assert "style_reference" in preview.variables
    assert "覆盖参考" in preview.variables["style_reference"]
    assert "样例小说" not in preview.variables["style_reference"]


def test_context_preview_service_rejects_missing_analysis_for_style_reference(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, inject_style_reference=False)
    service = create_context_preview_service()

    with pytest.raises(ContextBuilderError, match="style_reference analysis not found"):
        asyncio.run(
            service.preview_workflow_context(
                async_db(db),
                workflow.id,
                ContextPreviewRequestDTO(
                    node_id="chapter_gen",
                    chapter_number=1,
                    extra_inject=[
                        {
                            "type": "style_reference",
                            "analysis_id": "00000000-0000-0000-0000-000000000001",
                            "inject_fields": ["writing_style"],
                        }
                    ],
                ),
                owner_id=owner.id,
            )
        )


def test_context_preview_service_rejects_non_style_analysis_for_style_reference(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(
        db,
        owner=owner,
        inject_style_reference=True,
        analysis_type="plot",
    )
    service = create_context_preview_service()

    with pytest.raises(ContextBuilderError, match="style_reference requires style analysis"):
        asyncio.run(
            service.preview_workflow_context(
                async_db(db),
                workflow.id,
                ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
                owner_id=owner.id,
            )
        )


def _create_preview_workflow(
    db,
    *,
    owner,
    inject_style_reference: bool,
    analysis_type: str = "style",
    include_style_reference_prompt: bool = True,
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
    analysis = Analysis(
        project_id=project.id,
        analysis_type=analysis_type,
        source_title="样例小说",
        result={"writing_style": {"rhythm": "steady"}},
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    config_loader = ConfigLoader(CONFIG_ROOT)
    workflow_config = config_loader.load_workflow("workflow.xuanhuan_manual")
    chapter_gen = next(node for node in workflow_config.nodes if node.id == "chapter_gen")
    if inject_style_reference:
        chapter_gen.context_injection.append(
            ContextInjectionItem.model_validate(
                {
                    "type": "style_reference",
                    "analysis_id": str(analysis.id),
                    "inject_fields": ["writing_style"],
                }
            )
        )
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
