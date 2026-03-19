from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.content.models import Content, ContentVersion
from app.modules.project.models import Project

from tests.unit.models.helpers import create_project, create_user


def test_project_requires_owner_and_defaults(db):
    user = create_user(db, username="writer")
    project = Project(name="测试小说", owner_id=user.id, genre="玄幻")
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.owner_id == user.id
    assert project.status == "draft"
    assert project.deleted_at is None
    assert project.allow_system_credential_pool is False


def test_project_stores_project_setting(db):
    user = create_user(db, username="planner")
    project = Project(
        name="设定测试",
        owner_id=user.id,
        project_setting={
            "genre": "东方玄幻",
            "protagonist": {
                "name": "林渊",
                "identity": "寒门少年",
                "goal": "进入内门",
            },
            "world_setting": {
                "name": "九州大陆",
                "power_system": "灵气修炼",
            },
            "scale": {
                "target_words": 800000,
                "target_chapters": 200,
            },
        },
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.project_setting["protagonist"]["name"] == "林渊"
    assert project.project_setting["world_setting"]["name"] == "九州大陆"
    assert project.project_setting["scale"]["target_words"] == 800000


def test_project_rejects_project_setting_with_legacy_or_ambiguous_keys(db):
    user = create_user(db, username="planner-legacy")

    with pytest.raises(ValidationError):
        Project(
            name="错误设定",
            owner_id=user.id,
            project_setting={
                "worldview": "东方玄幻",
                "target_length": "200章",
                "protagonist": "林渊",
            },
        )


def test_project_soft_delete(db):
    project = create_project(db, name="要删除的项目")
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)

    assert project.deleted_at is not None


def test_content_creation(db):
    project = create_project(db, name="内容测试")
    content = Content(
        project_id=project.id,
        content_type="chapter",
        title="第一章",
        chapter_number=1,
        order_index=0,
    )
    db.add(content)
    db.commit()
    db.refresh(content)

    assert content.content_type == "chapter"
    assert content.chapter_number == 1
    assert content.status == "draft"


def test_content_version_tracking(db):
    project = create_project(db, name="版本测试")
    content = Content(project_id=project.id, content_type="outline", title="大纲")
    db.add(content)
    db.commit()

    version = ContentVersion(
        content_id=content.id,
        version_number=1,
        content_text="初版大纲内容",
        created_by="system",
        change_source="ai_generate",
        is_current=True,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    assert version.version_number == 1
    assert version.created_by == "system"
    assert version.change_source == "ai_generate"
    assert version.is_current is True
    assert version.context_snapshot_hash is None


def test_content_version_change_sources(db):
    project = create_project(db, name="编辑测试")
    content = Content(
        project_id=project.id,
        content_type="chapter",
        title="章节",
        chapter_number=1,
    )
    db.add(content)
    db.commit()

    change_cases = [
        ("system", "ai_generate"),
        ("user", "user_edit"),
        ("ai_assist", "ai_generate"),
        ("auto_fix", "ai_fix"),
    ]
    for index, (created_by, source) in enumerate(change_cases, start=1):
        db.add(
            ContentVersion(
                content_id=content.id,
                version_number=index,
                content_text=f"版本{index}",
                created_by=created_by,
                change_source=source,
                is_current=index == len(change_cases),
            )
        )

    db.commit()
    db.refresh(content)

    assert len(content.versions) == 4


def test_project_content_relationship(db):
    project = create_project(db, name="关系测试")
    db.add_all(
        [
            Content(project_id=project.id, content_type="outline", title="大纲"),
            Content(
                project_id=project.id,
                content_type="chapter",
                title="第一章",
                chapter_number=1,
            ),
        ]
    )
    db.commit()
    db.refresh(project)

    assert len(project.contents) == 2
