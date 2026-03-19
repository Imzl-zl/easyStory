import uuid

from sqlalchemy.orm import Session

from app.modules.content.models import Content, ContentVersion
from app.modules.project.models import Project
from app.modules.user.models import User
from app.modules.workflow.models import WorkflowExecution


def persist(db: Session, instance):
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def create_user(db: Session, **overrides) -> User:
    payload = {
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "hashed_password": "x",
    }
    payload.update(overrides)
    return persist(db, User(**payload))


def create_project(db: Session, **overrides) -> Project:
    owner = overrides.pop("owner", None) or create_user(db)
    payload = {
        "name": "测试项目",
        "owner_id": owner.id,
    }
    payload.update(overrides)
    return persist(db, Project(**payload))


def create_workflow(db: Session, **overrides) -> WorkflowExecution:
    project = overrides.pop("project", None) or create_project(db)
    payload = {
        "project_id": project.id,
        "status": "created",
    }
    payload.update(overrides)
    return persist(db, WorkflowExecution(**payload))


def create_content(db: Session, **overrides) -> Content:
    project = overrides.pop("project", None) or create_project(db)
    payload = {
        "project_id": project.id,
        "content_type": "chapter",
        "title": "第一章",
        "chapter_number": 1,
    }
    payload.update(overrides)
    return persist(db, Content(**payload))


def create_content_version(db: Session, **overrides) -> ContentVersion:
    content = overrides.pop("content", None) or create_content(db)
    payload = {
        "content_id": content.id,
        "version_number": 1,
        "content_text": "内容快照",
    }
    payload.update(overrides)
    return persist(db, ContentVersion(**payload))
