from __future__ import annotations

import asyncio
import copy
import shutil
import sys
import types
from typing import Any

import pytest

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import AgentConfig, HookConfig
from app.modules.observability.models import ExecutionLog
from app.modules.workflow.service.snapshot_support import freeze_agents, freeze_skills
from app.modules.workflow.service.workflow_hook_providers import (
    WebhookResponse,
    build_workflow_plugin_registry,
)
from app.shared.runtime.mcp.mcp_client import McpToolCallResult
from app.shared.runtime.plugins.plugin_registry import PluginRegistry
from app.shared.runtime.errors import ConfigurationError
from tests.unit.async_service_support import async_db
from tests.unit.test_workflow_runtime import (
    CONFIG_ROOT,
    _FakeToolProvider,
    _build_runtime_harness,
    _list_token_usages,
    _resume_and_run,
)


def test_runtime_after_generate_builtin_hook_logs_saved_candidate(db) -> None:
    harness = _build_runtime_harness(db)
    try:
        _run_to_chapter_generation(db, harness)
        logs = db.query(ExecutionLog).filter(ExecutionLog.message == "Hook executed").all()
        auto_save = next(item for item in logs if item.details["hook_id"] == "hook.auto_save")
        assert auto_save.details["event"] == "after_generate"
        assert auto_save.details["result"]["saved"] is True
        assert auto_save.details["result"]["content_id"]
        assert auto_save.details["result"]["content_version_id"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_after_generate_webhook_hook_posts_candidate_payload(db) -> None:
    captured: list[dict] = []

    async def sender(*, method: str, url: str, headers: dict[str, str], json_body):
        captured.append({"method": method, "url": url, "headers": headers, "json_body": json_body})
        return WebhookResponse(status_code=200, json_body={"ok": True}, text='{"ok":true}')

    harness = _build_runtime_harness(db)
    try:
        harness.runtime_service.plugin_registry = build_workflow_plugin_registry(
            harness.runtime_service,
            webhook_request_sender=sender,
        )
        _attach_hook(
            db,
            harness.workflow,
            "chapter_gen",
            "hook.webhook_probe",
            {
                "id": "hook.webhook_probe",
                "name": "Webhook Probe",
                "enabled": True,
                "trigger": {"event": "after_generate", "node_types": ["generate"]},
                "action": {
                    "type": "webhook",
                    "config": {"url": "https://example.com/hook", "method": "POST"},
                },
                "priority": 5,
                "timeout": 30,
            },
        )
        _run_to_chapter_generation(db, harness)
        assert len(captured) == 1
        assert captured[0]["method"] == "POST"
        assert captured[0]["json_body"]["content"]["id"]
        assert captured[0]["json_body"]["chapter"]["number"] == 1
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_after_generate_agent_hook_records_analysis_usage(db) -> None:
    harness = _build_runtime_harness(db)
    try:
        harness.runtime_service.tool_provider = _HookAwareToolProvider()
        _attach_hook(
            db,
            harness.workflow,
            "chapter_gen",
            "hook.agent_summary",
            {
                "id": "hook.agent_summary",
                "name": "Agent Summary",
                "enabled": True,
                "trigger": {"event": "after_generate", "node_types": ["generate"]},
                "action": {
                    "type": "agent",
                    "config": {
                        "agent_id": "agent.hook_summary",
                        "input_mapping": {
                            "chapter_number": "chapter.number",
                            "content": "content.text",
                        },
                    },
                },
                "priority": 4,
                "timeout": 30,
            },
        )
        _attach_agent_snapshot(
            db,
            harness.workflow,
            agent_id="agent.hook_summary",
            skill_id="skill.hook.summary",
        )
        _run_to_chapter_generation(db, harness)
        usages = _list_token_usages(db, harness.project_id)
        assert [item.usage_type for item in usages] == ["generate", "generate", "review", "analysis"]
        logs = db.query(ExecutionLog).filter(ExecutionLog.message == "Hook executed").all()
        assert any(item.details["hook_id"] == "hook.agent_summary" for item in logs)
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_hook_condition_skip_and_retry_are_visible(db) -> None:
    module_name = "tests.unit.dynamic_hook_runtime"
    state = {"condition_hits": 0, "retry_attempts": 0}
    module = types.ModuleType(module_name)

    def condition_counter(context, params):
        del context, params
        state["condition_hits"] += 1
        return {"called": True}

    def retry_once(context, params):
        del context, params
        state["retry_attempts"] += 1
        if state["retry_attempts"] == 1:
            raise RuntimeError("hook boom")
        return {"ok": True}

    module.condition_counter = condition_counter
    module.retry_once = retry_once
    sys.modules[module_name] = module
    harness = _build_runtime_harness(db)
    try:
        _attach_hook(
            db,
            harness.workflow,
            "chapter_gen",
            "hook.condition_skip",
            {
                "id": "hook.condition_skip",
                "name": "Condition Skip",
                "enabled": True,
                "trigger": {"event": "after_generate", "node_types": ["generate"]},
                "condition": {"field": "review.resolution", "operator": "==", "value": "skip"},
                "action": {"type": "script", "config": {"module": module_name, "function": "condition_counter"}},
                "priority": 2,
                "timeout": 30,
            },
        )
        _attach_hook(
            db,
            harness.workflow,
            "chapter_gen",
            "hook.retry_once",
            {
                "id": "hook.retry_once",
                "name": "Retry Once",
                "enabled": True,
                "trigger": {"event": "after_generate", "node_types": ["generate"]},
                "action": {"type": "script", "config": {"module": module_name, "function": "retry_once"}},
                "priority": 3,
                "timeout": 30,
                "retry": {"max_attempts": 2, "delay": 0},
            },
        )
        _run_to_chapter_generation(db, harness)
        assert state["condition_hits"] == 0
        assert state["retry_attempts"] == 2
        logs = db.query(ExecutionLog).filter(ExecutionLog.message == "Hook retry scheduled").all()
        assert any(item.details["hook_id"] == "hook.retry_once" for item in logs)
        skipped_logs = db.query(ExecutionLog).filter(ExecutionLog.message == "Hook skipped").all()
        assert any(item.details["hook_id"] == "hook.condition_skip" for item in skipped_logs)
    finally:
        sys.modules.pop(module_name, None)
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_after_node_end_webhook_hook_receives_node_outcome_payload(db) -> None:
    captured: list[dict] = []

    async def sender(*, method: str, url: str, headers: dict[str, str], json_body):
        captured.append({"method": method, "url": url, "headers": headers, "json_body": json_body})
        return WebhookResponse(status_code=200, json_body={"ok": True}, text='{"ok":true}')

    harness = _build_runtime_harness(db)
    try:
        harness.runtime_service.plugin_registry = build_workflow_plugin_registry(
            harness.runtime_service,
            webhook_request_sender=sender,
        )
        _attach_hook(
            db,
            harness.workflow,
            "chapter_gen",
            "hook.after_node_probe",
            {
                "id": "hook.after_node_probe",
                "name": "After Node Probe",
                "enabled": True,
                "trigger": {"event": "after_node_end", "node_types": ["generate"]},
                "action": {
                    "type": "webhook",
                    "config": {"url": "https://example.com/after-node", "method": "POST"},
                },
                "priority": 6,
                "timeout": 30,
            },
        )
        _run_to_chapter_generation(db, harness)
        assert len(captured) == 1
        payload = captured[0]["json_body"]
        assert payload["event"] == "after_node_end"
        assert payload["node"]["id"] == "chapter_gen"
        assert payload["node_execution_id"]
        assert payload["next_node_id"] == "chapter_gen"
        assert "pause_reason" in payload
        assert payload["chapter"]["number"] == 1
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_on_error_hook_failure_surfaces_exception_group(db) -> None:
    module_name = "tests.unit.dynamic_workflow_on_error"
    module = types.ModuleType(module_name)

    def before_fail(context, params):
        del context, params
        raise RuntimeError("before boom")

    def on_error_fail(context, params):
        del context, params
        raise RuntimeError("on_error boom")

    module.before_fail = before_fail
    module.on_error_fail = on_error_fail
    sys.modules[module_name] = module
    harness = _build_runtime_harness(db)
    try:
        _attach_hook(
            db,
            harness.workflow,
            "chapter_gen",
            "hook.before_fail",
            {
                "id": "hook.before_fail",
                "name": "Before Fail",
                "enabled": True,
                "trigger": {"event": "before_node_start", "node_types": ["generate"]},
                "action": {"type": "script", "config": {"module": module_name, "function": "before_fail"}},
                "priority": 1,
                "timeout": 30,
            },
            bucket="before",
        )
        _attach_hook(
            db,
            harness.workflow,
            "chapter_gen",
            "hook.on_error_fail",
            {
                "id": "hook.on_error_fail",
                "name": "On Error Fail",
                "enabled": True,
                "trigger": {"event": "on_error", "node_types": ["generate"]},
                "action": {"type": "script", "config": {"module": module_name, "function": "on_error_fail"}},
                "priority": 2,
                "timeout": 30,
            },
        )
        with pytest.raises(ExceptionGroup, match="Workflow runtime error and on_error hook both failed") as exc_info:
            _run_to_chapter_generation(db, harness)

        assert len(exc_info.value.exceptions) == 2
        assert str(exc_info.value.exceptions[0]) == "before boom"
        assert str(exc_info.value.exceptions[1]) == "on_error boom"
    finally:
        sys.modules.pop(module_name, None)
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_freeze_agents_includes_hook_agent_dependencies() -> None:
    base_loader = ConfigLoader(CONFIG_ROOT)
    workflow_config = base_loader.load_workflow("workflow.xuanhuan_manual").model_copy(deep=True)
    chapter_node = next(node for node in workflow_config.nodes if node.id == "chapter_gen")
    chapter_node.hooks.setdefault("after", []).append("hook.agent_summary")
    loader = _HookAwareLoader(base_loader)
    agents = freeze_agents(loader, workflow_config)
    skills = freeze_skills(loader, workflow_config, agents)
    assert {agent.id for agent in agents} >= {"agent.style_checker", "agent.hook_summary"}
    assert "skill.project_setting.conversation_extract" in skills


def test_plugin_registry_execute_honors_timeout() -> None:
    registry = PluginRegistry()
    registry.register("slow", _SlowProvider())

    async def run() -> None:
        with pytest.raises(asyncio.TimeoutError):
            await registry.execute("slow", config={}, context=None, timeout_seconds=0.01)

    asyncio.run(run())


async def test_workflow_plugin_registry_rejects_disabled_mcp_server() -> None:
    registry = build_workflow_plugin_registry(
        _NoopHookAgentRunner(),
        mcp_tool_caller=_UnexpectedMcpToolCaller(),
    )
    context = _StaticHookContext(
        {
            "resolved_mcp_servers": {
                "mcp.disabled": {
                    "id": "mcp.disabled",
                    "name": "Disabled MCP",
                    "transport": "streamable_http",
                    "url": "https://example.com/mcp",
                    "enabled": False,
                }
            }
        }
    )

    with pytest.raises(ConfigurationError, match="disabled"):
        await registry.execute(
            "mcp",
            config={"server_id": "mcp.disabled", "tool_name": "search_news"},
            context=context,
            timeout_seconds=30,
        )


async def test_workflow_plugin_registry_surfaces_mcp_is_error() -> None:
    registry = build_workflow_plugin_registry(
        _NoopHookAgentRunner(),
        mcp_tool_caller=_ErrorMcpToolCaller(),
    )
    context = _StaticHookContext(
        {
            "resolved_mcp_servers": {
                "mcp.enabled": {
                    "id": "mcp.enabled",
                    "name": "Enabled MCP",
                    "transport": "streamable_http",
                    "url": "https://example.com/mcp",
                    "enabled": True,
                }
            }
        }
    )

    with pytest.raises(RuntimeError, match="is_error=true"):
        await registry.execute(
            "mcp",
            config={"server_id": "mcp.enabled", "tool_name": "search_news"},
            context=context,
            timeout_seconds=30,
        )


def _run_to_chapter_generation(db, harness) -> None:
    asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
    db.commit()
    db.refresh(harness.workflow)
    _resume_and_run(db, harness)


def _attach_hook(
    db,
    workflow,
    node_id: str,
    hook_id: str,
    hook_config: dict,
    *,
    bucket: str = "after",
) -> None:
    snapshot = copy.deepcopy(workflow.workflow_snapshot)
    snapshot.setdefault("resolved_hooks", {})[hook_id] = copy.deepcopy(hook_config)
    for node in snapshot["nodes"]:
        if node["id"] != node_id:
            continue
        node.setdefault("hooks", {}).setdefault(bucket, []).append(hook_id)
        break
    workflow.workflow_snapshot = snapshot
    db.add(workflow)
    db.commit()
    db.refresh(workflow)


def _attach_agent_snapshot(db, workflow, *, agent_id: str, skill_id: str) -> None:
    agents = copy.deepcopy(workflow.agents_snapshot or {})
    agents[agent_id] = {
        "id": agent_id,
        "name": "Hook Summary Agent",
        "type": "checker",
        "system_prompt": "你是工作流 hook 摘要助手。",
        "skills": [skill_id],
        "model": {"provider": "openai", "name": "gpt-4o"},
    }
    skills = copy.deepcopy(workflow.skills_snapshot or {})
    skills[skill_id] = {
        "id": skill_id,
        "name": "Hook Summary Skill",
        "category": "utility",
        "prompt": "请用一句话总结第{{ chapter_number }}章：{{ content }}",
    }
    workflow.agents_snapshot = agents
    workflow.skills_snapshot = skills
    db.add(workflow)
    db.commit()
    db.refresh(workflow)


class _HookAwareToolProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        prompt = params["prompt"]
        model_name = params["model"].get("name") or params["credential"].get("default_model")
        if "请用一句话总结第" in prompt:
            return {
                "content": "第1章摘要：主角在夜色中踏上逃亡之路。",
                "model_name": model_name,
                "input_tokens": 6,
                "output_tokens": 12,
                "total_tokens": 18,
            }
        return await super().execute(tool_name, params)


class _HookAwareLoader:
    def __init__(self, base_loader: ConfigLoader) -> None:
        self.base_loader = base_loader

    def load_hook(self, hook_id: str):
        if hook_id != "hook.agent_summary":
            return self.base_loader.load_hook(hook_id)
        return HookConfig.model_validate(
            {
                "id": "hook.agent_summary",
                "name": "Agent Summary",
                "trigger": {"event": "after_generate", "node_types": ["generate"]},
                "action": {
                    "type": "agent",
                    "config": {"agent_id": "agent.hook_summary", "input_mapping": {}},
                },
            }
        )

    def load_agent(self, agent_id: str):
        if agent_id != "agent.hook_summary":
            return self.base_loader.load_agent(agent_id)
        return AgentConfig.model_validate(
            {
                "id": "agent.hook_summary",
                "name": "Hook Summary Agent",
                "type": "checker",
                "system_prompt": "你是工作流 hook 摘要助手。",
                "skills": ["skill.project_setting.conversation_extract"],
                "model": {"provider": "openai", "name": "gpt-4o"},
            }
        )

    def load_skill(self, skill_id: str):
        return self.base_loader.load_skill(skill_id)


class _SlowProvider:
    async def execute(self, *, config: dict, context) -> dict:
        del config, context
        await asyncio.sleep(0.05)
        return {"ok": True}


class _NoopHookAgentRunner:
    async def run_agent_hook(self, context, *, agent_id: str, input_mapping: dict[str, str]) -> Any:
        del context, agent_id, input_mapping
        raise AssertionError("agent hook runner should not be called in MCP provider tests")


class _UnexpectedMcpToolCaller:
    async def call_tool(self, *, server, tool_name: str, arguments: dict) -> McpToolCallResult:
        del server, tool_name, arguments
        raise AssertionError("disabled MCP server should fail before calling upstream")


class _ErrorMcpToolCaller:
    async def call_tool(self, *, server, tool_name: str, arguments: dict) -> McpToolCallResult:
        del server, tool_name, arguments
        return McpToolCallResult(
            content=[{"type": "text", "text": "上游返回 MCP 错误"}],
            structured_content={"message": "上游返回 MCP 错误"},
            is_error=True,
        )


class _StaticHookContext:
    def __init__(self, workflow_snapshot: dict[str, Any]) -> None:
        self.workflow = types.SimpleNamespace(workflow_snapshot=workflow_snapshot)

    def read_path(self, path: str) -> Any:
        raise AssertionError(f"unexpected read_path call: {path}")
