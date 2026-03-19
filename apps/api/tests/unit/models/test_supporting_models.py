import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.billing.models import TokenUsage
from app.modules.context.models import StoryFact
from app.modules.credential.models import ModelCredential
from app.modules.export.models import Export
from app.modules.observability.models import ExecutionLog, PromptReplay
from app.modules.template.models import TemplateNode
from app.modules.workflow.models import ChapterTask, NodeExecution

from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    create_template,
    create_workflow,
)


def test_chapter_task(db):
    workflow = create_workflow(db)
    chapter_task = ChapterTask(
        project_id=workflow.project_id,
        workflow_execution_id=workflow.id,
        chapter_number=1,
        title="第一章 废柴崛起",
        brief="主角觉醒天赋",
        key_characters=["萧炎", "萧薰儿"],
        key_events=["斗气觉醒"],
    )
    db.add(chapter_task)
    db.commit()
    db.refresh(chapter_task)

    assert chapter_task.chapter_number == 1
    assert chapter_task.status == "pending"
    assert chapter_task.key_characters == ["萧炎", "萧薰儿"]


def test_chapter_task_unique_per_workflow_and_chapter(db):
    workflow = create_workflow(db)
    db.add(
        ChapterTask(
            project_id=workflow.project_id,
            workflow_execution_id=workflow.id,
            chapter_number=1,
            title="第一章",
            brief="第一次规划",
        )
    )
    db.commit()
    db.add(
        ChapterTask(
            project_id=workflow.project_id,
            workflow_execution_id=workflow.id,
            chapter_number=1,
            title="第一章",
            brief="重复规划",
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()


def test_story_fact(db):
    project = create_project(db)
    content = create_content(
        db,
        project=project,
        content_type="chapter",
        title="第一章",
        chapter_number=1,
    )
    version = create_content_version(
        db,
        content=content,
        version_number=1,
        content_text="内容",
        created_by="system",
        change_source="ai_generate",
    )
    fact = StoryFact(
        project_id=project.id,
        chapter_number=1,
        source_content_version_id=version.id,
        fact_type="character_state",
        subject="萧炎",
        content="16岁，斗者三段",
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)

    assert fact.fact_type == "character_state"
    assert fact.is_active is True
    assert fact.superseded_by is None


def test_model_credential(db):
    credential = ModelCredential(
        owner_type="system",
        provider="anthropic",
        display_name="系统 Claude Key",
        encrypted_key="encrypted_data_here",
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)

    assert credential.owner_type == "system"
    assert credential.is_active is True
    assert credential.last_verified_at is None


def test_token_usage(db):
    project = create_project(db)
    credential = ModelCredential(
        owner_type="system",
        provider="openai",
        display_name="test",
        encrypted_key="x",
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)

    usage = TokenUsage(
        project_id=project.id,
        credential_id=credential.id,
        usage_type="generation",
        model_name="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        estimated_cost=0.015,
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)

    assert usage.usage_type == "generation"
    assert usage.input_tokens == 1000
    assert usage.estimated_cost == 0.015


def test_execution_log(db):
    workflow = create_workflow(db)
    log = ExecutionLog(
        workflow_execution_id=workflow.id,
        level="ERROR",
        message="LLM call failed",
        details={"error": "timeout"},
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    assert log.level == "ERROR"
    assert log.details["error"] == "timeout"


def test_prompt_replay(db):
    workflow = create_workflow(db)
    node = NodeExecution(
        workflow_execution_id=workflow.id,
        node_id="test",
        node_type="generate",
        sequence=0,
        node_order=0,
    )
    db.add(node)
    db.commit()

    replay = PromptReplay(
        node_execution_id=node.id,
        replay_type="generate",
        model_name="claude-sonnet-4-20250514",
        prompt_text="生成大纲",
        response_text="大纲内容...",
        input_tokens=100,
        output_tokens=500,
    )
    db.add(replay)
    db.commit()
    db.refresh(replay)

    assert replay.replay_type == "generate"
    assert replay.input_tokens == 100


def test_export(db):
    project = create_project(db)
    export = Export(
        project_id=project.id,
        format="markdown",
        filename="novel.md",
        file_path="novel.md",
        file_size=50000,
        config_snapshot={"include_metadata": True},
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    assert export.format == "markdown"
    assert export.file_size == 50000
    assert export.config_snapshot["include_metadata"] is True


def test_template_node_relationship(db):
    template = create_template(db)
    node = TemplateNode(
        template_id=template.id,
        node_order=1,
        node_type="generate",
        skill_id="skill.outline.xuanhuan",
        config={"temperature": 0.6},
        position_x=120,
        position_y=40,
    )
    db.add(node)
    db.commit()
    db.refresh(template)

    assert len(template.nodes) == 1
    assert template.nodes[0].skill_id == "skill.outline.xuanhuan"
