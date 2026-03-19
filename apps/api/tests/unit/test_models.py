import uuid

from app.models.user import User


def test_user_creation(db):
    user = User(username="testuser", hashed_password="hashed123")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.username == "testuser"
    assert user.id is not None
    assert user.is_active is True
    assert user.created_at is not None


def test_user_unique_username(db):
    u1 = User(username="unique_user", hashed_password="x")
    db.add(u1)
    db.commit()
    u2 = User(username="unique_user", hashed_password="y")
    db.add(u2)
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.commit()


def test_user_optional_email(db):
    user = User(username="no_email", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.email is None


def test_user_with_email(db):
    user = User(username="has_email", hashed_password="x", email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.email == "test@example.com"


from app.models.project import Project
from app.models.content import Content, ContentVersion


def test_project_requires_owner(db):
    from app.models.user import User
    user = User(username="writer", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="测试小说", owner_id=user.id, genre="玄幻")
    db.add(project)
    db.commit()
    db.refresh(project)
    assert project.owner_id == user.id
    assert project.status == "draft"
    assert project.deleted_at is None


def test_project_soft_delete(db):
    from app.models.user import User
    from datetime import datetime, timezone
    user = User(username="deleter", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="要删除的项目", owner_id=user.id)
    db.add(project)
    db.commit()
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    assert project.deleted_at is not None


def test_content_creation(db):
    from app.models.user import User
    user = User(username="author", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="内容测试", owner_id=user.id)
    db.add(project)
    db.commit()
    content = Content(
        project_id=project.id, content_type="chapter",
        title="第一章", chapter_number=1, order_index=0,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    assert content.content_type == "chapter"
    assert content.chapter_number == 1
    assert content.status == "draft"


def test_content_version_tracking(db):
    from app.models.user import User
    user = User(username="versioner", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="版本测试", owner_id=user.id)
    db.add(project)
    db.commit()
    content = Content(project_id=project.id, content_type="outline", title="大纲")
    db.add(content)
    db.commit()
    v1 = ContentVersion(
        content_id=content.id, version_number=1,
        content_text="初版大纲内容",
        created_by="system",
        change_source="ai_generate",
        is_current=True,
    )
    db.add(v1)
    db.commit()
    db.refresh(v1)
    assert v1.version_number == 1
    assert v1.created_by == "system"
    assert v1.change_source == "ai_generate"
    assert v1.is_current is True
    assert v1.context_snapshot_hash is None


def test_content_version_change_sources(db):
    from app.models.user import User
    user = User(username="editor", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="编辑测试", owner_id=user.id)
    db.add(project)
    db.commit()
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
    for i, (created_by, source) in enumerate(change_cases, start=1):
        v = ContentVersion(
            content_id=content.id, version_number=i,
            content_text=f"版本{i}",
            created_by=created_by,
            change_source=source,
            is_current=i == len(change_cases),
        )
        db.add(v)
    db.commit()
    db.refresh(content)
    assert len(content.versions) == 4


def test_project_content_relationship(db):
    from app.models.user import User
    user = User(username="relator", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="关系测试", owner_id=user.id)
    db.add(project)
    db.commit()
    c1 = Content(project_id=project.id, content_type="outline", title="大纲")
    c2 = Content(project_id=project.id, content_type="chapter", title="第一章", chapter_number=1)
    db.add_all([c1, c2])
    db.commit()
    db.refresh(project)
    assert len(project.contents) == 2


# ─── Workflow / Node / Artifact / Review tests ───────────────────────

import pytest
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from app.models.workflow import WorkflowExecution, NodeExecution
from app.models.artifact import Artifact
from app.models.review import ReviewAction


def _make_project(db):
    """辅助函数: 创建 user + project"""
    from app.models.user import User
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="测试项目", owner_id=user.id)
    db.add(project)
    db.commit()
    return project


def _make_workflow(db):
    """辅助函数: 创建 project + workflow_execution"""
    project = _make_project(db)
    wf = WorkflowExecution(project_id=project.id, status="created")
    db.add(wf)
    db.commit()
    return wf


def test_workflow_execution_defaults(db):
    wf = _make_workflow(db)
    db.refresh(wf)
    assert wf.status == "created"
    assert wf.current_node_id is None
    assert wf.pause_reason is None
    assert wf.workflow_snapshot is None


def test_workflow_execution_with_snapshots(db):
    project = _make_project(db)
    wf = WorkflowExecution(
        project_id=project.id, status="running",
        workflow_snapshot={"id": "wf.test", "nodes": []},
        skills_snapshot={"skill.outline": {}},
        agents_snapshot={"agent.checker": {}},
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    assert wf.workflow_snapshot["id"] == "wf.test"
    assert "skill.outline" in wf.skills_snapshot


def test_node_execution_basic(db):
    wf = _make_workflow(db)
    node = NodeExecution(
        workflow_execution_id=wf.id, node_id="outline",
        node_type="generate", sequence=0, node_order=0,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    assert node.status == "pending"
    assert node.retry_count == 0


def test_node_execution_unique_constraint(db):
    wf = _make_workflow(db)
    n1 = NodeExecution(
        workflow_execution_id=wf.id, node_id="outline",
        node_type="generate", sequence=0, node_order=0,
    )
    db.add(n1)
    db.commit()
    n2 = NodeExecution(
        workflow_execution_id=wf.id, node_id="outline",
        node_type="generate", sequence=0, node_order=0,
    )
    db.add(n2)
    with pytest.raises(SAIntegrityError):
        db.commit()


def test_node_execution_different_sequence_ok(db):
    wf = _make_workflow(db)
    n1 = NodeExecution(
        workflow_execution_id=wf.id, node_id="chapter_1",
        node_type="generate", sequence=0, node_order=0,
    )
    n2 = NodeExecution(
        workflow_execution_id=wf.id, node_id="chapter_1",
        node_type="generate", sequence=1, node_order=0,
    )
    db.add_all([n1, n2])
    db.commit()
    assert n1.id != n2.id


def test_artifact_belongs_to_node(db):
    wf = _make_workflow(db)
    node = NodeExecution(
        workflow_execution_id=wf.id, node_id="outline",
        node_type="generate", sequence=0, node_order=0,
    )
    db.add(node)
    db.commit()
    artifact = Artifact(
        node_execution_id=node.id, artifact_type="outline",
        content="大纲内容...", word_count=500,
    )
    db.add(artifact)
    db.commit()
    db.refresh(node)
    assert len(node.artifacts) == 1
    assert node.artifacts[0].word_count == 500


def test_review_action_with_issues(db):
    wf = _make_workflow(db)
    node = NodeExecution(
        workflow_execution_id=wf.id, node_id="chapter_1",
        node_type="generate", sequence=0, node_order=0,
    )
    db.add(node)
    db.commit()
    review = ReviewAction(
        node_execution_id=node.id, agent_id="agent.style_checker",
        review_type="style_check", result="failed",
        issues={"items": [{"category": "style_deviation", "severity": "major"}]},
    )
    db.add(review)
    db.commit()
    db.refresh(node)
    assert len(node.review_actions) == 1
    assert node.review_actions[0].result == "failed"
    assert node.review_actions[0].issues["items"][0]["severity"] == "major"


def test_workflow_node_relationship(db):
    wf = _make_workflow(db)
    n1 = NodeExecution(
        workflow_execution_id=wf.id, node_id="outline",
        node_type="generate", sequence=0, node_order=0, status="completed",
    )
    n2 = NodeExecution(
        workflow_execution_id=wf.id, node_id="chapter_1",
        node_type="generate", sequence=0, node_order=1, status="pending",
    )
    db.add_all([n1, n2])
    db.commit()
    db.refresh(wf)
    assert len(wf.node_executions) == 2


# ─── Support model tests ─────────────────────────────────────────────

from app.models.chapter_task import ChapterTask
from app.models.story_fact import StoryFact
from app.models.token_usage import TokenUsage
from app.models.credential import ModelCredential
from app.models.execution_log import ExecutionLog, PromptReplay
from app.models.export import Export


def test_chapter_task(db):
    wf = _make_workflow(db)
    ct = ChapterTask(
        project_id=wf.project_id,
        workflow_execution_id=wf.id,
        chapter_number=1,
        title="第一章 废柴崛起", brief="主角觉醒天赋",
        key_characters=["萧炎", "萧薰儿"],
        key_events=["斗气觉醒"],
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    assert ct.chapter_number == 1
    assert ct.status == "pending"
    assert ct.key_characters == ["萧炎", "萧薰儿"]


def test_story_fact(db):
    project = _make_project(db)
    content = Content(
        project_id=project.id,
        content_type="chapter",
        title="ch1",
        chapter_number=1,
    )
    db.add(content)
    db.commit()
    version = ContentVersion(
        content_id=content.id,
        version_number=1,
        content_text="内容",
        created_by="system",
        change_source="ai_generate",
    )
    db.add(version)
    db.commit()
    fact = StoryFact(
        project_id=project.id, chapter_number=1,
        source_content_version_id=version.id,
        fact_type="character_state", subject="萧炎",
        content="16岁，斗者三段",
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)
    assert fact.fact_type == "character_state"
    assert fact.is_active is True
    assert fact.superseded_by is None


def test_model_credential(db):
    cred = ModelCredential(
        owner_type="system", provider="anthropic",
        display_name="系统 Claude Key",
        encrypted_key="encrypted_data_here",
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    assert cred.owner_type == "system"
    assert cred.is_active is True
    assert cred.last_verified_at is None


def test_token_usage(db):
    project = _make_project(db)
    cred = ModelCredential(
        owner_type="system", provider="openai",
        display_name="test", encrypted_key="x",
    )
    db.add(cred)
    db.commit()
    usage = TokenUsage(
        project_id=project.id, credential_id=cred.id,
        model_name="gpt-4o", input_tokens=1000,
        output_tokens=500, estimated_cost=0.015,
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)
    assert usage.input_tokens == 1000
    assert usage.estimated_cost == 0.015


def test_execution_log(db):
    wf = _make_workflow(db)
    log = ExecutionLog(
        workflow_execution_id=wf.id, level="ERROR",
        message="LLM call failed", details={"error": "timeout"},
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    assert log.level == "ERROR"
    assert log.details["error"] == "timeout"


def test_prompt_replay(db):
    wf = _make_workflow(db)
    node = NodeExecution(
        workflow_execution_id=wf.id, node_id="test",
        node_type="generate", sequence=0, node_order=0,
    )
    db.add(node)
    db.commit()
    replay = PromptReplay(
        node_execution_id=node.id, replay_type="generate",
        model_name="claude-sonnet-4-20250514",
        prompt_text="生成大纲", response_text="大纲内容...",
        input_tokens=100, output_tokens=500,
    )
    db.add(replay)
    db.commit()
    db.refresh(replay)
    assert replay.replay_type == "generate"
    assert replay.input_tokens == 100


def test_export(db):
    project = _make_project(db)
    exp = Export(
        project_id=project.id, format="markdown",
        filename="novel.md", file_path="novel.md",
        file_size=50000,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    assert exp.format == "markdown"
    assert exp.file_size == 50000
