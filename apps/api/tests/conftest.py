import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.content import Content, ContentVersion  # noqa: F401
from app.models.workflow import WorkflowExecution, NodeExecution  # noqa: F401
from app.models.artifact import Artifact  # noqa: F401
from app.models.review import ReviewAction  # noqa: F401
from app.models.chapter_task import ChapterTask  # noqa: F401
from app.models.story_fact import StoryFact  # noqa: F401
from app.models.token_usage import TokenUsage  # noqa: F401
from app.models.credential import ModelCredential  # noqa: F401
from app.models.execution_log import ExecutionLog, PromptReplay  # noqa: F401
from app.models.export import Export  # noqa: F401


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session
