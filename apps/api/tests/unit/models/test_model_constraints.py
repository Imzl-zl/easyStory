import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.content.models import Content, ContentVersion
from app.modules.workflow.models import WorkflowExecution

from tests.unit.models.helpers import create_content, create_project


def test_workflow_execution_enforces_single_active_workflow_per_project(db):
    project = create_project(db)
    db.add(
        WorkflowExecution(
            project_id=project.id,
            status="running",
            current_node_id="outline",
        )
    )
    db.commit()
    db.add(
        WorkflowExecution(
            project_id=project.id,
            status="paused",
            current_node_id="chapter_gen",
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()


def test_workflow_execution_allows_completed_history_for_same_project(db):
    project = create_project(db)
    db.add(WorkflowExecution(project_id=project.id, status="completed"))
    db.commit()
    db.add(WorkflowExecution(project_id=project.id, status="created"))
    db.commit()


def test_content_enforces_single_outline_and_opening_plan_per_project(db):
    project = create_project(db)
    db.add(Content(project_id=project.id, content_type="outline", title="大纲"))
    db.commit()
    db.add(Content(project_id=project.id, content_type="outline", title="第二份大纲"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    db.add(
        Content(project_id=project.id, content_type="opening_plan", title="开篇设计")
    )
    db.commit()
    db.add(
        Content(
            project_id=project.id,
            content_type="opening_plan",
            title="第二份开篇设计",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_content_enforces_unique_chapter_number_per_project(db):
    project = create_project(db)
    create_content(db, project=project, title="第一章")
    db.add(
        Content(
            project_id=project.id,
            content_type="chapter",
            title="重复第一章",
            chapter_number=1,
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    ("content_type", "chapter_number"),
    [("chapter", None), ("outline", 1), ("opening_plan", 1)],
)
def test_content_enforces_chapter_number_shape(db, content_type, chapter_number):
    project = create_project(db)
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
    project = create_project(db)
    content = create_content(db, project=project)
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
    project = create_project(db)
    content = create_content(db, project=project)
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
