import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.content import Content, ContentVersion
from app.models.project import Project
from app.models.user import User
from app.models.workflow import WorkflowExecution


def _create_project(db) -> Project:
    user = User(username=f"user_{uuid.uuid4().hex[:8]}", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="约束测试项目", owner_id=user.id)
    db.add(project)
    db.commit()
    return project


def _create_content(db, project_id, **overrides) -> Content:
    payload = {
        "project_id": project_id,
        "content_type": "chapter",
        "title": "第一章",
        "chapter_number": 1,
    }
    payload.update(overrides)
    content = Content(**payload)
    db.add(content)
    return content


def test_workflow_execution_enforces_single_active_workflow_per_project(db):
    project = _create_project(db)
    db.add(WorkflowExecution(project_id=project.id, status="running", current_node_id="outline"))
    db.commit()
    db.add(WorkflowExecution(project_id=project.id, status="paused", current_node_id="chapter_gen"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_workflow_execution_allows_completed_history_for_same_project(db):
    project = _create_project(db)
    db.add(WorkflowExecution(project_id=project.id, status="completed"))
    db.commit()
    db.add(WorkflowExecution(project_id=project.id, status="created"))
    db.commit()


def test_content_enforces_single_outline_and_opening_plan_per_project(db):
    project = _create_project(db)
    db.add(Content(project_id=project.id, content_type="outline", title="大纲"))
    db.commit()
    db.add(Content(project_id=project.id, content_type="outline", title="第二份大纲"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(Content(project_id=project.id, content_type="opening_plan", title="开篇设计"))
    db.commit()
    db.add(Content(project_id=project.id, content_type="opening_plan", title="第二份开篇设计"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_content_enforces_unique_chapter_number_per_project(db):
    project = _create_project(db)
    _create_content(db, project.id, title="第一章")
    db.commit()
    _create_content(db, project.id, title="重复第一章")
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    ("content_type", "chapter_number"),
    [("chapter", None), ("outline", 1), ("opening_plan", 1)],
)
def test_content_enforces_chapter_number_shape(db, content_type, chapter_number):
    project = _create_project(db)
    db.add(
        Content(
            project_id=project.id,
            content_type=content_type,
            title="非法内容",
            chapter_number=chapter_number,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_content_version_allows_only_one_current_version(db):
    project = _create_project(db)
    content = _create_content(db, project.id)
    db.commit()
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text="v1",
            is_current=True,
        )
    )
    db.commit()
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=2,
            content_text="v2",
            is_current=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_content_version_allows_only_one_best_version(db):
    project = _create_project(db)
    content = _create_content(db, project.id)
    db.commit()
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text="v1",
            is_current=True,
            is_best=True,
        )
    )
    db.commit()
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=2,
            content_text="v2",
            is_current=False,
            is_best=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
