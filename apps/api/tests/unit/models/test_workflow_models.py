import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.content.models import Content, ContentVersion
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import Artifact, NodeExecution, WorkflowExecution

from tests.unit.models.helpers import create_project, create_template, create_workflow


def test_workflow_execution_defaults(db):
    workflow = create_workflow(db)

    assert workflow.status == "created"
    assert workflow.current_node_id is None
    assert workflow.pause_reason is None
    assert workflow.workflow_snapshot is None


def test_workflow_execution_with_snapshots(db):
    project = create_project(db)
    template = create_template(db)
    workflow = WorkflowExecution(
        project_id=project.id,
        template_id=template.id,
        status="running",
        workflow_snapshot={"id": "wf.test", "nodes": []},
        skills_snapshot={"skill.outline": {}},
        agents_snapshot={"agent.checker": {}},
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    assert workflow.workflow_snapshot["id"] == "wf.test"
    assert "skill.outline" in workflow.skills_snapshot
    assert workflow.template_id == template.id


def test_project_and_workflow_can_reference_template(db):
    template = create_template(db)
    project = create_project(db, template_id=template.id)
    workflow = create_workflow(db, project=project, template_id=template.id)

    db.refresh(project)
    db.refresh(workflow)

    assert project.template is not None
    assert workflow.template is not None
    assert project.template.id == template.id
    assert workflow.template.id == template.id


def test_node_execution_basic(db):
    workflow = create_workflow(db)
    node = NodeExecution(
        workflow_execution_id=workflow.id,
        node_id="outline",
        node_type="generate",
        sequence=0,
        node_order=0,
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    assert node.status == "pending"
    assert node.retry_count == 0


def test_node_execution_unique_constraint(db):
    workflow = create_workflow(db)
    db.add(
        NodeExecution(
            workflow_execution_id=workflow.id,
            node_id="outline",
            node_type="generate",
            sequence=0,
            node_order=0,
        )
    )
    db.commit()
    db.add(
        NodeExecution(
            workflow_execution_id=workflow.id,
            node_id="outline",
            node_type="generate",
            sequence=0,
            node_order=0,
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()


def test_node_execution_different_sequence_ok(db):
    workflow = create_workflow(db)
    db.add_all(
        [
            NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="chapter_1",
                node_type="generate",
                sequence=0,
                node_order=0,
            ),
            NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="chapter_1",
                node_type="generate",
                sequence=1,
                node_order=0,
            ),
        ]
    )
    db.commit()

    nodes = db.query(NodeExecution).filter_by(workflow_execution_id=workflow.id).all()
    assert len(nodes) == 2


def test_artifact_belongs_to_node(db):
    workflow = create_workflow(db)
    node = NodeExecution(
        workflow_execution_id=workflow.id,
        node_id="outline",
        node_type="generate",
        sequence=0,
        node_order=0,
    )
    db.add(node)
    db.commit()

    content = Content(
        project_id=workflow.project_id,
        content_type="outline",
        title="大纲",
    )
    db.add(content)
    db.commit()
    version = ContentVersion(
        content_id=content.id,
        version_number=1,
        content_text="大纲内容",
    )
    db.add(version)
    db.commit()

    artifact = Artifact(
        node_execution_id=node.id,
        artifact_type="content_version_ref",
        content_version_id=version.id,
        payload={"excerpt": "大纲内容"},
        word_count=500,
    )
    db.add(artifact)
    db.commit()
    db.refresh(node)

    assert len(node.artifacts) == 1
    assert node.artifacts[0].content_version_id == version.id
    assert node.artifacts[0].payload["excerpt"] == "大纲内容"


def test_review_action_with_issues(db):
    workflow = create_workflow(db)
    node = NodeExecution(
        workflow_execution_id=workflow.id,
        node_id="chapter_1",
        node_type="generate",
        sequence=0,
        node_order=0,
    )
    db.add(node)
    db.commit()

    review = ReviewAction(
        node_execution_id=node.id,
        agent_id="agent.style_checker",
        reviewer_name="style-checker",
        review_type="style_check",
        status="failed",
        summary="文风偏移明显",
        issues={"items": [{"category": "style_deviation", "severity": "major"}]},
        execution_time_ms=1200,
        tokens_used=300,
    )
    db.add(review)
    db.commit()
    db.refresh(node)

    assert len(node.review_actions) == 1
    assert node.review_actions[0].status == "failed"
    assert node.review_actions[0].summary == "文风偏移明显"
    assert node.review_actions[0].issues["items"][0]["severity"] == "major"


def test_workflow_node_relationship(db):
    workflow = create_workflow(db)
    db.add_all(
        [
            NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="outline",
                node_type="generate",
                sequence=0,
                node_order=0,
                status="completed",
            ),
            NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="chapter_1",
                node_type="generate",
                sequence=0,
                node_order=1,
                status="pending",
            ),
        ]
    )
    db.commit()
    db.refresh(workflow)

    assert len(workflow.node_executions) == 2
