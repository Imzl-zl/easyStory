import asyncio

from app.modules.content.models import Content, ContentVersion
import pytest

from app.modules.project.infrastructure import ProjectDocumentFileStore
from app.modules.project.service import (
    ProjectDocumentSaveDTO,
    ProjectService,
    ProjectSettingUpdateDTO,
)
from app.shared.runtime.errors import BusinessRuleError
from tests.unit.async_service_support import async_db

from tests.unit.models.helpers import (
    create_chapter_task,
    create_content,
    create_content_version,
    create_project,
    create_workflow,
    ready_project_setting,
)


def test_update_project_setting_marks_derived_assets_stale_when_summary_changes(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(
            protagonist={"name": "林渊", "identity": "少年", "goal": "变强"},
            world_setting={"world_rules": "灵气修炼"},
            core_conflict="宗门压制",
            scale={"target_words": 500000},
        ),
    )
    workflow = create_workflow(db, project=project)
    outline = create_content(
        db,
        project=project,
        content_type="outline",
        title="大纲",
        chapter_number=None,
    )
    outline.status = "approved"
    outline.chapter_number = None
    opening_plan = create_content(
        db,
        project=project,
        content_type="opening_plan",
        title="开篇设计",
        chapter_number=None,
    )
    opening_plan.status = "approved"
    chapter = create_content(db, project=project, title="第一章")
    chapter.status = "approved"
    chapter_task = create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        title="第一章",
        brief="旧章节计划",
        status="pending",
    )
    db.commit()
    create_content_version(db, content=outline, content_text="旧大纲", version_number=1)
    create_content_version(
        db,
        content=opening_plan,
        content_text="旧开篇",
        version_number=1,
    )

    result = asyncio.run(
        ProjectService().update_project_setting(
            async_db(db),
            project.id,
            ProjectSettingUpdateDTO(
                project_setting={
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
                    "scale": {"target_words": 800000},
                }
            ),
        )
    )

    db.refresh(project)
    db.refresh(outline)
    db.refresh(opening_plan)
    db.refresh(chapter)
    db.refresh(chapter_task)

    assert result.genre == "仙侠"
    assert result.target_words == 800000
    assert result.impact.has_impact is True
    assert result.impact.total_affected_entries == 4
    assert [item.target for item in result.impact.items] == [
        "outline",
        "opening_plan",
        "chapter",
        "chapter_tasks",
    ]
    assert project.genre == "仙侠"
    assert project.target_words == 800000
    assert outline.status == "stale"
    assert opening_plan.status == "stale"
    assert chapter.status == "stale"
    assert chapter_task.status == "stale"


def test_update_project_setting_returns_empty_impact_when_value_is_unchanged(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(),
    )

    result = asyncio.run(
        ProjectService().update_project_setting(
            async_db(db),
            project.id,
            ProjectSettingUpdateDTO(project_setting=ready_project_setting()),
        )
    )

    assert result.impact.has_impact is False
    assert result.impact.total_affected_entries == 0
    assert result.impact.items == []


def test_check_setting_completeness_returns_warning_issues_for_summary_gaps(db):
    project = create_project(
        db,
        project_setting={
            "genre": "玄幻",
            "protagonist": {"name": "林渊"},
        },
    )

    result = asyncio.run(ProjectService().check_setting_completeness(async_db(db), project.id))

    issue_fields = {issue.field: issue.level for issue in result.issues}
    assert result.status == "warning"
    assert issue_fields["protagonist.identity"] == "warning"
    assert issue_fields["protagonist.goal"] == "warning"
    assert issue_fields["core_conflict"] == "warning"
    assert issue_fields["world_setting"] == "warning"
    assert issue_fields["tone"] == "warning"
    assert issue_fields["scale"] == "warning"


def test_get_preparation_status_points_to_outline_when_project_summary_is_incomplete(db):
    project = create_project(
        db,
        project_setting={"genre": "玄幻"},
    )

    result = asyncio.run(ProjectService().get_preparation_status(async_db(db), project.id))

    assert result.setting.status == "warning"
    assert result.outline.step_status == "not_started"
    assert result.opening_plan.step_status == "not_started"
    assert result.chapter_tasks.step_status == "not_started"
    assert result.can_start_workflow is False
    assert result.next_step == "outline"


def test_get_preparation_status_identifies_workflow_gate_when_assets_ready(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(),
    )
    _create_story_asset(db, project.id, "outline", "approved", "主线大纲")
    _create_story_asset(db, project.id, "opening_plan", "approved", "前三章开篇设计")

    result = asyncio.run(ProjectService().get_preparation_status(async_db(db), project.id))

    assert result.setting.status == "ready"
    assert result.outline.step_status == "approved"
    assert result.opening_plan.step_status == "approved"
    assert result.chapter_tasks.step_status == "not_started"
    assert result.can_start_workflow is True
    assert result.next_step == "workflow"


def test_get_preparation_status_flags_stale_tasks_under_active_workflow(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(),
    )
    workflow = create_workflow(
        db,
        project=project,
        status="paused",
        current_node_id="chapter_gen",
    )
    _create_story_asset(db, project.id, "outline", "approved", "主线大纲")
    _create_story_asset(db, project.id, "opening_plan", "approved", "前三章开篇设计")
    create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        title="第一章",
        brief="旧任务",
        status="stale",
    )

    result = asyncio.run(ProjectService().get_preparation_status(async_db(db), project.id))

    assert result.active_workflow is not None
    assert result.active_workflow.execution_id == workflow.id
    assert result.chapter_tasks.step_status == "stale"
    assert result.chapter_tasks.counts.stale == 1
    assert result.can_start_workflow is False
    assert result.next_step == "chapter_tasks"


def test_get_project_document_uses_outline_seed_when_file_missing(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    _create_story_asset(db, project.id, "outline", "approved", "这是从数据库回填的大纲内容")

    result = asyncio.run(
        ProjectService(
            document_file_store=ProjectDocumentFileStore(tmp_path),
        ).get_project_document(
            async_db(db),
            project.id,
            "大纲/总大纲.md",
        )
    )

    assert result.source == "outline"
    assert result.content == "这是从数据库回填的大纲内容"
    assert result.updated_at is None


def test_get_project_document_ignores_shadow_file_for_canonical_outline_path(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    _create_story_asset(db, project.id, "outline", "approved", "这是数据库中的正式大纲")
    file_store = ProjectDocumentFileStore(tmp_path)
    file_store.save_project_document(project.id, "大纲/总大纲.md", "这是旧的影子文件")

    result = asyncio.run(
        ProjectService(document_file_store=file_store).get_project_document(
            async_db(db),
            project.id,
            "大纲/总大纲.md",
        )
    )

    assert result.source == "outline"
    assert result.content == "这是数据库中的正式大纲"


def test_save_project_document_persists_markdown_file(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    service = ProjectService(document_file_store=ProjectDocumentFileStore(tmp_path))

    saved = asyncio.run(
        service.save_project_document(
            async_db(db),
            project.id,
            "设定/世界观.md",
            ProjectDocumentSaveDTO(content="# 世界观\n\n这里是文件保存后的内容。"),
        )
    )
    loaded = asyncio.run(
        service.get_project_document(
            async_db(db),
            project.id,
            "设定/世界观.md",
        )
    )

    assert saved.source == "file"
    assert loaded.source == "file"
    assert loaded.content == "# 世界观\n\n这里是文件保存后的内容。"
    assert (tmp_path / "projects" / str(project.id) / "documents" / "设定" / "世界观.md").exists()


def test_save_project_document_rejects_canonical_content_paths(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    service = ProjectService(document_file_store=ProjectDocumentFileStore(tmp_path))

    with pytest.raises(BusinessRuleError, match="正式内容真值"):
        asyncio.run(
            service.save_project_document(
                async_db(db),
                project.id,
                "正文/第001章.md",
                ProjectDocumentSaveDTO(content="# 正文\n\n不应该写到文件层"),
            )
        )


def test_save_project_document_rejects_parent_path_escape(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    service = ProjectService(document_file_store=ProjectDocumentFileStore(tmp_path))

    with pytest.raises(BusinessRuleError, match="非法目录跳转"):
        asyncio.run(
            service.save_project_document(
                async_db(db),
                project.id,
                "../逃逸.md",
                ProjectDocumentSaveDTO(content="不应该写出项目目录"),
            )
        )


def _create_story_asset(
    db,
    project_id,
    content_type: str,
    status: str,
    content_text: str,
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title="大纲" if content_type == "outline" else "开篇设计",
        chapter_number=None,
        status=status,
    )
    db.add(content)
    db.flush()
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=content_text,
            is_current=True,
        )
    )
    db.commit()
