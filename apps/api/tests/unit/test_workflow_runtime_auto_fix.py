from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.modules.billing.service import create_billing_service
from app.modules.config_registry import ConfigLoader
from app.modules.content.models import Content
from app.modules.content.service import create_chapter_content_service
from app.modules.context.engine import create_context_builder
from app.modules.export.service import ExportService
from app.modules.observability.models import PromptReplay
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.modules.workflow.service.factory import create_workflow_service
from app.modules.workflow.service.workflow_runtime_service import WorkflowRuntimeService
from app.modules.workflow.service.snapshot_support import (
    dump_config,
    freeze_agents,
    freeze_skills,
    freeze_workflow,
    resolve_start_node_id,
)
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.tool_provider import ToolProvider
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_template, create_user, ready_project_setting
from tests.unit.test_workflow_runtime import (
    CONFIG_ROOT,
    RuntimeHarness,
    _FakeCredentialService,
    _create_asset,
    _list_chapter_tasks,
    _list_node_executions,
    _list_token_usages,
    _require_chapter,
    _require_current_version,
    _resume_and_run,
)


def test_runtime_auto_fix_re_reviews_and_persists_fixed_candidate(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(
            initial_content="第一章正文：这里有违禁词。",
            fixed_content="第一章正文：净化后的正文。",
            pass_on_fixed=True,
        ),
        auto_fix=True,
        max_fix_attempts=2,
        on_fix_fail="pause",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter = _require_chapter(db, harness.project_id, 1)
        version = _require_current_version(chapter)
        review_actions = db.query(ReviewAction).order_by(ReviewAction.created_at.asc()).all()
        prompt_replays = _chapter_gen_replays(db, harness.workflow.id)
        node_executions = _list_node_executions(db, harness.workflow.id)
        token_usages = _list_token_usages(db, harness.project_id)

        assert harness.workflow.status == "paused"
        assert harness.workflow.current_node_id == "chapter_gen"
        assert harness.workflow.resume_from_node == "chapter_gen"
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["generating"]
        assert version.created_by == "auto_fix"
        assert version.change_source == "ai_fix"
        assert version.change_summary == "自动精修后通过复审"
        assert "净化后的正文" in version.content_text
        assert [item.review_type for item in review_actions] == ["auto_review", "auto_re_review_1"]
        assert [item.status for item in review_actions] == ["failed", "passed"]
        assert [item.replay_type for item in prompt_replays] == ["generate", "fix"]
        assert [item.status for item in node_executions] == ["completed", "completed"]
        assert [item.usage_type for item in token_usages] == ["generate", "generate", "review", "fix", "review"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_review_failed_candidate_stays_confirmable_without_auto_fix(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(initial_content="第一章正文：这里有违禁词。"),
        auto_fix=False,
        max_fix_attempts=1,
        on_fix_fail="pause",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter = _require_chapter(db, harness.project_id, 1)
        version = _require_current_version(chapter)
        node_executions = _list_node_executions(db, harness.workflow.id)

        assert harness.workflow.status == "paused"
        assert harness.workflow.pause_reason == "review_failed"
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["generating"]
        assert version.created_by == "ai_assist"
        assert version.change_source == "ai_generate"
        assert [item.status for item in node_executions] == ["completed", "failed"]

        asyncio.run(harness.chapter_content_service.approve_chapter(async_db(db), harness.project_id, 1))
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["completed"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_auto_fix_pause_keeps_candidate_and_uses_review_failed_reason(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(
            initial_content="第一章正文：这里有违禁词。",
            fixed_content="第一章正文：修完依然有违禁词。",
            pass_on_fixed=False,
        ),
        auto_fix=True,
        max_fix_attempts=1,
        on_fix_fail="pause",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter = _require_chapter(db, harness.project_id, 1)
        version = _require_current_version(chapter)
        prompt_replays = _chapter_gen_replays(db, harness.workflow.id)
        node_executions = _list_node_executions(db, harness.workflow.id)

        assert harness.workflow.status == "paused"
        assert harness.workflow.pause_reason == "review_failed"
        assert harness.workflow.snapshot["pending_actions"][0]["type"] == "chapter_confirmation"
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["generating"]
        assert version.created_by == "auto_fix"
        assert version.change_source == "ai_fix"
        assert version.change_summary == "自动精修最终候选"
        assert [item.replay_type for item in prompt_replays] == ["generate", "fix"]
        assert [item.status for item in node_executions] == ["completed", "failed"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_auto_fix_skip_drops_candidate_and_completes_workflow(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(
            initial_content="第一章正文：这里有违禁词。",
            fixed_content="第一章正文：修完依然有违禁词。",
            pass_on_fixed=False,
        ),
        auto_fix=True,
        max_fix_attempts=1,
        on_fix_fail="skip",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        prompt_replays = _chapter_gen_replays(db, harness.workflow.id)
        review_actions = db.query(ReviewAction).order_by(ReviewAction.created_at.asc()).all()
        node_executions = _list_node_executions(db, harness.workflow.id)

        assert harness.workflow.status == "completed"
        assert db.query(Content).filter(Content.project_id == harness.project_id, Content.content_type == "chapter").all() == []
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["skipped"]
        assert [item.status for item in node_executions] == ["completed", "skipped"]
        assert [item.status for item in review_actions] == ["failed", "failed"]
        assert [item.replay_type for item in prompt_replays] == ["generate", "fix"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_auto_fix_fail_can_resume_after_user_approves_final_candidate(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(
            initial_content="第一章正文：这里有违禁词。",
            fixed_content="第一章正文：修完依然有违禁词。",
            pass_on_fixed=False,
        ),
        auto_fix=True,
        max_fix_attempts=1,
        on_fix_fail="fail",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter = _require_chapter(db, harness.project_id, 1)

        assert harness.workflow.status == "failed"
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["failed"]

        asyncio.run(harness.chapter_content_service.approve_chapter(async_db(db), harness.project_id, 1))
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["completed"]

        harness.workflow_service.resume(harness.workflow)
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        db.refresh(chapter)

        assert harness.workflow.status == "completed"
        assert len(chapter.versions) == 1
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_budget_pause_keeps_generated_candidate_and_stops_before_review(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(initial_content="第一章正文：预算刚好打满。"),
        auto_fix=False,
        max_fix_attempts=1,
        on_fix_fail="pause",
        budget_max_tokens_per_workflow=60,
        budget_on_exceed="pause",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter = _require_chapter(db, harness.project_id, 1)
        version = _require_current_version(chapter)
        token_usages = _list_token_usages(db, harness.project_id)

        assert harness.workflow.status == "paused"
        assert harness.workflow.pause_reason == "budget_exceeded"
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["generating"]
        assert version.change_source == "ai_generate"
        assert db.query(ReviewAction).all() == []
        assert [item.usage_type for item in token_usages] == ["generate", "generate"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_budget_pause_persists_completed_review_actions_before_interrupt(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(
            initial_content="第一章正文：预算在第二个 reviewer 处中断。",
            review_always_pass=True,
        ),
        auto_fix=False,
        max_fix_attempts=1,
        on_fix_fail="pause",
        budget_max_tokens_per_workflow=90,
        budget_on_exceed="pause",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        chapter_gen = next(
            node for node in harness.workflow.workflow_snapshot["nodes"] if node["id"] == "chapter_gen"
        )
        chapter_gen["review_mode"] = "serial"
        chapter_gen["reviewers"] = ["agent.style_checker", "agent.style_checker"]
        _resume_and_run(db, harness)
        chapter = _require_chapter(db, harness.project_id, 1)
        version = _require_current_version(chapter)
        review_actions = db.query(ReviewAction).order_by(ReviewAction.created_at.asc()).all()
        token_usages = _list_token_usages(db, harness.project_id)

        assert harness.workflow.status == "paused"
        assert harness.workflow.pause_reason == "budget_exceeded"
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["generating"]
        assert version.change_source == "ai_generate"
        assert [item.status for item in review_actions] == ["passed"]
        assert [item.review_type for item in review_actions] == ["auto_review"]
        assert [item.usage_type for item in token_usages] == ["generate", "generate", "review", "review"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_budget_skip_marks_chapter_skipped_without_review(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(initial_content="第一章正文：预算跳过。"),
        auto_fix=False,
        max_fix_attempts=1,
        on_fix_fail="pause",
        budget_max_tokens_per_workflow=60,
        budget_on_exceed="skip",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)

        assert harness.workflow.status == "completed"
        assert db.query(Content).filter(Content.project_id == harness.project_id, Content.content_type == "chapter").all() == []
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["skipped"]
        assert db.query(ReviewAction).all() == []
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_budget_fail_keeps_candidate_and_fails_workflow(db) -> None:
    harness = _build_auto_fix_harness(
        db,
        _ReviewCycleToolProvider(initial_content="第一章正文：预算失败。"),
        auto_fix=False,
        max_fix_attempts=1,
        on_fix_fail="pause",
        budget_max_tokens_per_workflow=60,
        budget_on_exceed="fail",
    )
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter = _require_chapter(db, harness.project_id, 1)

        assert harness.workflow.status == "failed"
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == ["failed"]
        assert _require_current_version(chapter).change_source == "ai_generate"
        assert db.query(ReviewAction).all() == []
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def _build_auto_fix_harness(
    db: Session,
    tool_provider: ToolProvider,
    *,
    auto_fix: bool,
    max_fix_attempts: int,
    on_fix_fail: str,
    budget_max_tokens_per_node: int | None = None,
    budget_max_tokens_per_workflow: int | None = None,
    budget_on_exceed: str = "pause",
) -> RuntimeHarness:
    owner = create_user(db)
    template = create_template(db)
    project = create_project(
        db,
        owner=owner,
        template_id=template.id,
        project_setting=ready_project_setting(),
    )
    _create_asset(db, project.id, "outline", "大纲")
    _create_asset(db, project.id, "opening_plan", "开篇设计")
    config_loader = ConfigLoader(CONFIG_ROOT)
    workflow_config = config_loader.load_workflow("workflow.xuanhuan_manual")
    workflow_config.nodes = [node for node in workflow_config.nodes if node.id != "export"]
    chapter_gen = next(node for node in workflow_config.nodes if node.id == "chapter_gen")
    chapter_gen.auto_fix = auto_fix
    chapter_gen.max_fix_attempts = max_fix_attempts
    chapter_gen.on_fix_fail = on_fix_fail
    if budget_max_tokens_per_node is not None:
        workflow_config.budget.max_tokens_per_node = budget_max_tokens_per_node
    if budget_max_tokens_per_workflow is not None:
        workflow_config.budget.max_tokens_per_workflow = budget_max_tokens_per_workflow
    workflow_config.budget.on_exceed = budget_on_exceed
    agents = freeze_agents(config_loader, workflow_config)
    workflow = WorkflowExecution(
        project_id=project.id,
        template_id=project.template_id,
        status="created",
        workflow_snapshot=freeze_workflow(config_loader, workflow_config),
        skills_snapshot=freeze_skills(config_loader, workflow_config, agents),
        agents_snapshot={agent.id: dump_config(agent) for agent in agents},
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    workflow_service = create_workflow_service()
    workflow_service.start(workflow, current_node_id=resolve_start_node_id(workflow_config))
    export_root = Path.cwd() / ".pytest-exports" / f"workflow-runtime-autofix-{uuid.uuid4().hex}"
    runtime_service = WorkflowRuntimeService(
        workflow_service=workflow_service,
        billing_service=create_billing_service(),
        chapter_content_service=create_chapter_content_service(),
        context_builder=create_context_builder(),
        credential_service_factory=lambda: _FakeCredentialService(),
        export_service=ExportService(export_root),
        template_renderer=SkillTemplateRenderer(),
        tool_provider=tool_provider,
    )
    db.commit()
    db.refresh(workflow)
    return RuntimeHarness(
        chapter_content_service=create_chapter_content_service(),
        export_root=export_root,
        owner_id=owner.id,
        project_id=project.id,
        runtime_service=runtime_service,
        workflow=workflow,
        workflow_service=workflow_service,
    )


class _ReviewCycleToolProvider(ToolProvider):
    def __init__(
        self,
        *,
        initial_content: str,
        fixed_content: str | None = None,
        pass_on_fixed: bool = False,
        review_always_pass: bool = False,
    ) -> None:
        self.initial_content = initial_content
        self.fixed_content = fixed_content
        self.pass_on_fixed = pass_on_fixed
        self.review_always_pass = review_always_pass

    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        prompt = params["prompt"]
        if "请拆分出可执行的章节任务列表" in prompt:
            return {
                "content": json.dumps(
                    {
                        "chapters": [
                            {
                                "chapter_number": 1,
                                "title": "第一章 试炼夜",
                                "brief": "主角第一次试炼",
                                "key_characters": ["林渊"],
                                "key_events": ["试炼"],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "input_tokens": 6,
                "output_tokens": 12,
                "total_tokens": 18,
            }
        if "输出一个严格符合 ReviewResult 的 JSON 对象" in prompt:
            return {
                "content": self._review_result(prompt),
                "input_tokens": 8,
                "output_tokens": 8,
                "total_tokens": 16,
            }
        if "你是小说精修编辑" in prompt:
            assert self.fixed_content is not None
            return {
                "content": self.fixed_content,
                "input_tokens": 20,
                "output_tokens": 30,
                "total_tokens": 50,
            }
        return {
            "content": self.initial_content,
            "input_tokens": 12,
            "output_tokens": 36,
            "total_tokens": 48,
        }

    def list_tools(self) -> list[str]:
        return ["llm.generate"]

    def _review_result(self, prompt: str) -> dict:
        if self.review_always_pass or (
            self.pass_on_fixed and self.fixed_content and self.fixed_content in prompt
        ):
            return {
                "reviewer_id": "agent.style_checker",
                "reviewer_name": "文风检查员",
                "status": "passed",
                "score": 95,
                "issues": [],
                "summary": "通过",
                "execution_time_ms": 1,
                "tokens_used": 10,
            }
        return {
            "reviewer_id": "agent.style_checker",
            "reviewer_name": "文风检查员",
            "status": "failed",
            "score": 40,
            "issues": [
                {
                    "category": "banned_words",
                    "severity": "critical",
                    "description": "正文包含违禁词",
                    "suggested_fix": "移除违禁词并重写该句",
                }
            ],
            "summary": "存在违禁词",
            "execution_time_ms": 1,
            "tokens_used": 10,
        }


def _chapter_gen_replays(db: Session, workflow_id: uuid.UUID) -> list[PromptReplay]:
    return (
        db.query(PromptReplay)
        .join(NodeExecution, PromptReplay.node_execution_id == NodeExecution.id)
        .filter(
            NodeExecution.workflow_execution_id == workflow_id,
            NodeExecution.node_id == "chapter_gen",
        )
        .order_by(PromptReplay.created_at.asc())
        .all()
    )
