from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import textwrap
import uuid

import pytest
from pydantic import ValidationError

from app.modules.assistant.service.assistant_config_file_store import AssistantConfigFileStore
from app.modules.assistant.service.agents.assistant_agent_dto import AssistantAgentCreateDTO
from app.modules.assistant.service.agents.assistant_agent_file_store import AssistantAgentFileStore
from app.modules.assistant.service.agents.assistant_agent_service import AssistantAgentService
from app.modules.assistant.service.hooks.assistant_hook_dto import AssistantHookCreateDTO
from app.modules.assistant.service.hooks.assistant_hook_file_store import AssistantHookFileStore
from app.modules.assistant.service.hooks.assistant_hook_service import AssistantHookService
from app.modules.assistant.service.hooks_runtime.assistant_hook_providers import (
    build_assistant_plugin_registry,
)
from app.modules.assistant.service.mcp.assistant_mcp_dto import AssistantMcpCreateDTO
from app.modules.assistant.service.mcp.assistant_mcp_file_store import AssistantMcpFileStore
from app.modules.assistant.service.mcp.assistant_mcp_service import AssistantMcpService
from app.modules.assistant.service.skills.assistant_skill_dto import AssistantSkillCreateDTO
from app.modules.assistant.service.skills.assistant_skill_file_store import (
    AssistantSkillFileStore,
)
from app.modules.assistant.service.skills.assistant_skill_service import (
    AssistantSkillService,
)
from app.modules.assistant.service.assistant_service import AssistantService, AssistantStreamEvent
from app.modules.assistant.service.turn.assistant_turn_run_store import AssistantTurnRunStore
from app.modules.assistant.service.tooling.assistant_tool_executor import AssistantToolExecutor
from app.modules.assistant.service.tooling.assistant_tool_exposure_policy import AssistantToolExposurePolicy
from app.modules.assistant.service.tooling.assistant_tool_loop import AssistantToolLoop
from app.modules.assistant.service.tooling.assistant_tool_registry import AssistantToolDescriptorRegistry
from app.modules.assistant.service.tooling.assistant_tool_step_store import AssistantToolStepStore
from app.modules.assistant.service.turn.assistant_turn_runtime_support import (
    build_after_assistant_payload,
    build_turn_run_id,
)
from app.modules.assistant.service.turn.assistant_turn_error_support import (
    build_request_error_hook_payload,
)
from app.modules.assistant.service.context.assistant_prompt_support import (
    build_document_context_injection_snapshot,
)
from app.modules.assistant.service.rules.assistant_rule_dto import AssistantRuleProfileUpdateDTO
from app.modules.assistant.service.preferences.preferences_dto import (
    AssistantPreferencesUpdateDTO,
)
from app.modules.assistant.service.preferences.preferences_service import (
    AssistantPreferencesService,
)
from app.modules.assistant.service.dto import (
    AssistantContinuationAnchorDTO,
    AssistantMessageDTO,
    AssistantTurnRequestDTO,
    build_structured_items_digest,
    build_turn_messages_digest,
)
from app.modules.assistant.service.factory import create_assistant_rule_service
from app.modules.config_registry import ConfigLoader
from app.modules.credential.models import ModelCredential
from app.modules.project.infrastructure import (
    ProjectDocumentFileStore,
    ProjectDocumentIdentityStore,
    ProjectDocumentRevisionStore,
)
from app.modules.project.service import ProjectDocumentCapabilityService, ProjectService, create_project_service
from app.modules.project.service.project_document_buffer_state_support import (
    TRUSTED_ACTIVE_BUFFER_SOURCE,
    build_project_document_buffer_hash,
)
from app.shared.runtime import McpToolCallResult, SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMStreamEvent
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError
from tests.unit.assistant_service_test_support import (
    _build_config_root,
    _build_turn_request,
    _CompactingCredentialService,
    _FakeCredentialService,
    _InteropProfileCredentialService,
    _TextOnlyCredentialService,
    _write_yaml,
)
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user


class _FailOnCommittedStepStore(AssistantToolStepStore):
    def append_step(self, record) -> None:
        if record.status == "committed":
            raise RuntimeError("failed to persist committed snapshot")
        super().append_step(record)


class _FailOnAppendRevisionStore(ProjectDocumentRevisionStore):
    def append_revision(self, *args, **kwargs):
        raise RuntimeError("failed to append revision")

    def append_revision_unlocked(self, *args, **kwargs):
        raise RuntimeError("failed to append revision")


def _write_turn_run_snapshot(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_rule_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def _expected_run_budget(
    *,
    max_steps: int,
    tool_timeout_seconds: int | None,
    max_tool_calls: int | None = None,
    max_input_tokens: int | None = None,
    max_history_tokens: int | None = None,
) -> dict[str, object]:
    return {
        "max_steps": max_steps,
        "max_tool_calls": max_steps if max_tool_calls is None else max_tool_calls,
        "max_input_tokens": max_input_tokens,
        "max_history_tokens": max_history_tokens,
        "max_tool_schema_tokens": None,
        "max_tool_result_tokens_per_step": None,
        "max_read_bytes": None,
        "max_write_bytes": None,
        "max_parallel_tool_calls": 1,
        "tool_timeout_seconds": tool_timeout_seconds,
    }


def _build_trusted_active_buffer_state(
    *,
    base_version: str,
    content: str,
    dirty: bool = False,
) -> dict[str, object]:
    return {
        "dirty": dirty,
        "base_version": base_version,
        "buffer_hash": build_project_document_buffer_hash(content),
        "source": TRUSTED_ACTIVE_BUFFER_SOURCE,
    }


def test_assistant_turn_request_rejects_write_targets_when_scope_disabled() -> None:
    with pytest.raises(ValidationError, match="unsupported_write_target_scope"):
        _build_turn_request(
            messages=[AssistantMessageDTO(role="user", content="test")],
            document_context={
                "active_document_ref": "project_file:test",
            },
            requested_write_targets=["project_file:test"],
        )


class _FakeToolProvider(ToolProvider):
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.requests: list[dict[str, object | None]] = []

    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        prompt = params["prompt"]
        self.prompts.append(prompt)
        self.requests.append(
            {
                "prompt": prompt,
                "response_format": params["response_format"],
                "system_prompt": params.get("system_prompt"),
                "model": params.get("model"),
                "credential": params.get("credential"),
                "tools": params.get("tools"),
                "continuation_items": params.get("continuation_items"),
                "provider_continuation_state": params.get("provider_continuation_state"),
            }
        )
        if "请输出结构化摘要" in prompt:
            return {
                "content": '{"summary":"今天的新闻聚焦科技与国际局势。","sentiment":"neutral"}',
                "input_tokens": 4,
                "output_tokens": 8,
                "total_tokens": 12,
            }
        if "请根据以下内容输出一句摘要" in prompt:
            return {"content": "Hook 摘要完成。", "input_tokens": 3, "output_tokens": 5, "total_tokens": 8}
        return {
            "content": "主回复：今天的重点新闻主要集中在科技和国际动态。",
            "model_name": "gpt-4o-mini",
            "input_tokens": 11,
            "output_tokens": 19,
            "total_tokens": 30,
        }

    async def execute_stream(self, tool_name: str, params: dict, *, should_stop=None):
        del should_stop
        result = await self.execute(tool_name, params)
        content = result["content"]
        midpoint = max(1, len(content) // 2)
        yield LLMStreamEvent(delta=content[:midpoint])
        yield LLMStreamEvent(delta=content[midpoint:])
        yield LLMStreamEvent(response=result)

    def list_tools(self) -> list[str]:
        return ["llm.generate"]


def _request_contains_continuation_fragment(params: dict, fragment: str) -> bool:
    continuation_items = params.get("continuation_items")
    if not isinstance(continuation_items, list):
        return False
    serialized = json.dumps(continuation_items, ensure_ascii=False, sort_keys=True)
    return fragment in serialized


class _ToolCallingFakeToolProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        result = await super().execute(tool_name, params)
        prompt = params["prompt"]
        tools = params.get("tools") or []
        if tools and not params.get("continuation_items") and "读一下人物设定" in prompt:
            return {
                "content": "",
                "model_name": "gpt-4o-mini",
                "input_tokens": 12,
                "output_tokens": 4,
                "total_tokens": 16,
                "tool_calls": [
                    {
                        "tool_call_id": "call.project.read_documents.1",
                        "tool_name": "project.read_documents",
                        "arguments": {"paths": ["设定/人物.md"]},
                        "arguments_text": '{"paths":["设定/人物.md"]}',
                        "provider_ref": "fc_001",
                    }
                ],
                "provider_response_id": "resp_tool_1",
            }
        if (
            _request_contains_continuation_fragment(params, "设定/人物.md")
            and _request_contains_continuation_fragment(params, "林渊")
        ):
            return {
                "content": "我已经读完人物设定。主角林渊是个冷静克制、擅长观察细节的人物，可以把悬疑开场压在他的感官判断上。",
                "model_name": "gpt-4o-mini",
                "input_tokens": 20,
                "output_tokens": 18,
                "total_tokens": 38,
                "provider_response_id": "resp_tool_2",
            }
        return result

    async def execute_stream(self, tool_name: str, params: dict, *, should_stop=None):
        del should_stop
        result = await self.execute(tool_name, params)
        if result.get("tool_calls"):
            yield LLMStreamEvent(response=result)
            return
        content = result["content"]
        midpoint = max(1, len(content) // 2)
        yield LLMStreamEvent(delta=content[:midpoint])
        yield LLMStreamEvent(delta=content[midpoint:])
        yield LLMStreamEvent(response=result)


class _ToolCallingCompactionProvider(_ToolCallingFakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        result = await super().execute(tool_name, params)
        if params.get("tools") and params.get("continuation_items"):
            return {
                "content": "我已经读完人物设定，可以继续推进开场。",
                "model_name": "gpt-4o-mini",
                "input_tokens": 23,
                "output_tokens": 12,
                "total_tokens": 35,
                "provider_response_id": "resp_tool_2",
            }
        return result


class _ToolLoopErrorEchoProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        result = await super().execute(tool_name, params)
        prompt = params["prompt"]
        tools = params.get("tools") or []
        if tools and not params.get("continuation_items") and "找一下人物和缺失文稿" in prompt:
            return {
                "content": "",
                "model_name": "gpt-4o-mini",
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
                "tool_calls": [
                    {
                        "tool_call_id": "call.project.read_documents.mixed",
                        "tool_name": "project.read_documents",
                        "arguments": {"paths": ["设定/人物.md", "设定/不存在.md"]},
                        "arguments_text": '{"paths":["设定/人物.md","设定/不存在.md"]}',
                        "provider_ref": "fc_mixed",
                    }
                ],
            }
        if (
            _request_contains_continuation_fragment(params, "document_not_found")
            and _request_contains_continuation_fragment(params, "设定/不存在.md")
        ):
            return {
                "content": "我看到人物文稿已读到，但设定/不存在.md 读取失败，请先确认路径。",
                "model_name": "gpt-4o-mini",
                "input_tokens": 16,
                "output_tokens": 10,
                "total_tokens": 26,
            }
        return result


class _InfiniteToolCallProvider(_FakeToolProvider):
    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    async def execute(self, tool_name: str, params: dict) -> dict:
        await super().execute(tool_name, params)
        self.call_count += 1
        return {
            "content": "",
            "model_name": "gpt-4o-mini",
            "input_tokens": 9,
            "output_tokens": 3,
            "total_tokens": 12,
            "tool_calls": [
                {
                    "tool_call_id": f"call.project.read_documents.loop-{self.call_count}",
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物.md"]},
                    "arguments_text": '{"paths":["设定/人物.md"]}',
                    "provider_ref": f"fc_loop_{self.call_count}",
                }
            ],
        }


class _ParallelToolCallProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        await super().execute(tool_name, params)
        if _request_contains_continuation_fragment(params, "call.project.read_documents.2"):
            return {
                "content": "我已按顺序读取人物设定，可以继续给出分析。",
                "model_name": "gpt-4o-mini",
                "input_tokens": 12,
                "output_tokens": 10,
                "total_tokens": 22,
            }
        return {
            "content": "",
            "model_name": "gpt-4o-mini",
            "input_tokens": 9,
            "output_tokens": 3,
            "total_tokens": 12,
            "tool_calls": [
                {
                    "tool_call_id": "call.project.read_documents.1",
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物.md"]},
                    "arguments_text": '{"paths":["设定/人物.md"]}',
                    "provider_ref": "fc_parallel_1",
                },
                {
                    "tool_call_id": "call.project.read_documents.2",
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物.md"]},
                    "arguments_text": '{"paths":["设定/人物.md"]}',
                    "provider_ref": "fc_parallel_2",
                },
            ],
        }


class _WriteDocumentToolProvider(_FakeToolProvider):
    def __init__(self, *, base_version: str) -> None:
        super().__init__()
        self.base_version = base_version

    async def execute(self, tool_name: str, params: dict) -> dict:
        result = await super().execute(tool_name, params)
        prompt = params["prompt"]
        tools = params.get("tools") or []
        if tools and not params.get("continuation_items") and "把当前人物设定补一条观察能力" in prompt:
            return {
                "content": "",
                "model_name": "gpt-4o-mini",
                "input_tokens": 11,
                "output_tokens": 5,
                "total_tokens": 16,
                "tool_calls": [
                    {
                        "tool_call_id": "call.project.write_document.1",
                        "tool_name": "project.write_document",
                        "arguments": {
                            "path": "设定/人物.md",
                            "content": "# 人物\n\n林渊：冷静、克制。\n\n补充：他对雨夜里的细微异常尤其敏感。",
                            "base_version": self.base_version,
                        },
                        "arguments_text": '{"path":"设定/人物.md","content":"# 人物\\n\\n林渊：冷静、克制。\\n\\n补充：他对雨夜里的细微异常尤其敏感。","base_version":"'
                        + self.base_version
                        + '"}',
                        "provider_ref": "fc_write_1",
                    }
                ],
            }
        if (
            _request_contains_continuation_fragment(params, "project.write_document")
            and _request_contains_continuation_fragment(params, "document_revision_id")
        ):
            return {
                "content": "人物设定已经同步到当前文稿，可以继续基于新设定推进开场。",
                "model_name": "gpt-4o-mini",
                "input_tokens": 13,
                "output_tokens": 11,
                "total_tokens": 24,
            }
        return result


class _WriteConflictToolProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        result = await super().execute(tool_name, params)
        prompt = params["prompt"]
        tools = params.get("tools") or []
        if tools and not params.get("continuation_items") and "尝试覆盖旧版本人物设定" in prompt:
            return {
                "content": "",
                "model_name": "gpt-4o-mini",
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
                "tool_calls": [
                    {
                        "tool_call_id": "call.project.write_document.conflict",
                        "tool_name": "project.write_document",
                        "arguments": {
                            "path": "设定/人物.md",
                            "content": "# 人物\n\n错误覆盖内容",
                            "base_version": "sha256:stale",
                        },
                        "arguments_text": '{"path":"设定/人物.md","content":"# 人物\\n\\n错误覆盖内容","base_version":"sha256:stale"}',
                        "provider_ref": "fc_write_conflict",
                    }
                ],
            }
        if _request_contains_continuation_fragment(params, "version_conflict"):
            return {
                "content": "写回失败，因为人物设定已经有新版本，应该先读取最新内容再决定是否覆盖。",
                "model_name": "gpt-4o-mini",
                "input_tokens": 12,
                "output_tokens": 12,
                "total_tokens": 24,
            }
        return result


class _ToolLoopCompactingCredentialService(_FakeCredentialService):
    async def resolve_active_credential(self, db, *, provider: str, user_id, project_id=None):
        del db, user_id, project_id
        return ModelCredential(
            owner_type="user",
            owner_id=uuid.uuid4(),
            provider=provider,
            display_name=f"{provider}-tool-loop-compacting-test",
            encrypted_key=f"{provider}-key",
            api_dialect="openai_responses",
            default_model="gpt-4o-mini",
            interop_profile="responses_strict",
            context_window_tokens=1600,
            stream_tool_verified_probe_kind="tool_continuation_probe",
            buffered_tool_verified_probe_kind="tool_continuation_probe",
            is_active=True,
        )

class _ProjectStreamingFakeToolProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        result = await super().execute(tool_name, params)
        if params["prompt"].endswith("给我一个冷峻克制的开场方向。"):
            return {
                "content": "第一句。第二句。第三句。",
                "model_name": "gpt-4o-mini",
                "input_tokens": 10,
                "output_tokens": 12,
                "total_tokens": 22,
            }
        return result

    async def execute_stream(self, tool_name: str, params: dict, *, should_stop=None):
        del should_stop
        result = await self.execute(tool_name, params)
        if result["content"] == "第一句。第二句。第三句。":
            yield LLMStreamEvent(delta="第一句。")
            yield LLMStreamEvent(delta="第二句。")
            yield LLMStreamEvent(delta="第三句。")
            yield LLMStreamEvent(response=result)
            return
        async for event in super().execute_stream(tool_name, params, should_stop=None):
            yield event


class _FailingProjectStreamToolProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        prompt = params["prompt"]
        self.prompts.append(prompt)
        self.requests.append(
            {
                "prompt": prompt,
                "response_format": params["response_format"],
                "system_prompt": params.get("system_prompt"),
                "model": params.get("model"),
                "tools": params.get("tools"),
            }
        )
        if "请根据以下内容输出一句摘要" in prompt:
            return {
                "content": "Hook 摘要完成。",
                "input_tokens": 3,
                "output_tokens": 5,
                "total_tokens": 8,
            }
        if "故意触发流式失败" in prompt:
            raise ConfigurationError("上游流式失败")
        return {
            "content": "主回复：今天的重点新闻主要集中在科技和国际动态。",
            "model_name": "gpt-4o-mini",
            "input_tokens": 11,
            "output_tokens": 19,
            "total_tokens": 30,
        }


class _EmptyContentToolProvider(_FakeToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        result = await super().execute(tool_name, params)
        if "请根据以下内容输出一句摘要" in params["prompt"]:
            return result
        return {
            "content": None,
            "model_name": "gpt-4o-mini",
            "input_tokens": 8,
            "output_tokens": 0,
            "total_tokens": 8,
        }

    async def execute_stream(self, tool_name: str, params: dict, *, should_stop=None):
        del should_stop
        result = await self.execute(tool_name, params)
        yield LLMStreamEvent(response=result)


class _FakeMcpToolCaller:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    async def call_tool(self, *, server, tool_name: str, arguments: dict) -> McpToolCallResult:
        self.calls.append((server.id, tool_name, arguments))
        return McpToolCallResult(
            content=[{"type": "text", "text": "来自 MCP 的查询结果"}],
            structured_content={"headline": "今日热点"},
            is_error=False,
        )


class _ErrorMcpToolCaller(_FakeMcpToolCaller):
    async def call_tool(self, *, server, tool_name: str, arguments: dict) -> McpToolCallResult:
        self.calls.append((server.id, tool_name, arguments))
        return McpToolCallResult(
            content=[{"type": "text", "text": "上游返回错误"}],
            structured_content={"message": "上游返回错误"},
            is_error=True,
        )

async def test_assistant_service_runs_skill_and_mcp_hook(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    mcp_tool_caller = _FakeMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    mcp_service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    service = AssistantService(
        assistant_mcp_service=mcp_service,
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        mcp_server_resolver=lambda context, server_id: mcp_service.resolve_mcp_server(
            server_id,
            owner_id=context.owner_id,
        ),
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-service")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                agent_id="agent.general_assistant",
                hook_ids=["hook.before_news_lookup"],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.content.startswith("主回复：")
        assert response.conversation_id == "conversation-test"
        assert response.client_turn_id.startswith("turn-")
        assert response.output_items[0].item_type == "text"
        assert response.skill_id == "skill.assistant.general_chat"
        assert response.mcp_servers == ["mcp.news.lookup"]
        assert response.hook_results[0].action_type == "mcp"
        assert mcp_tool_caller.calls == [
            ("mcp.news.lookup", "search_news", {"query": "今天有什么新闻？"})
        ]
        assert "今天有什么新闻？" in tool_provider.prompts[0]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_uses_project_skill_for_project_turn(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_skill_service=skill_service,
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-skill-runtime")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        project_skill_file = (
            tmp_path
            / "assistant-config"
            / "projects"
            / str(project.id)
            / "skills"
            / "skill.assistant.general_chat"
            / "SKILL.md"
        )
        project_skill_file.parent.mkdir(parents=True, exist_ok=True)
        project_skill_file.write_text(
            "\n".join(
                    [
                        "---",
                        "id: skill.assistant.general_chat",
                        "name: 项目聊天",
                        "enabled: true",
                        "model:",
                        "  provider: openai",
                        "  name: gpt-4o-mini",
                        "---",
                    "",
                    "项目层先给一句方向判断，再继续展开。",
                    "用户输入：{{ user_input }}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        async with async_session_factory() as session:
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                project_id=project.id,
                messages=[AssistantMessageDTO(role="user", content="我想写一个悬疑故事")],
            )
            response = await service.turn(session, payload, owner_id=owner.id)

        assert response.skill_id == "skill.assistant.general_chat"
        assert "项目层先给一句方向判断" in tool_provider.prompts[0]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_skill_prompt_appends_missing_history_context(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_skill_service=skill_service,
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-skill-history-append")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created_skill = await skill_service.create_user_skill(
                session,
                AssistantSkillCreateDTO(
                    name="只看当前输入",
                    content="先给一个判断，再接着回答。\n用户输入：{{ user_input }}",
                ),
                owner_id=owner.id,
            )
            payload = _build_turn_request(
                skill_id=created_skill.id,
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[
                    AssistantMessageDTO(role="user", content="上一版太平了。"),
                    AssistantMessageDTO(role="assistant", content="主要问题是冲突没有持续升级。"),
                    AssistantMessageDTO(role="user", content="这一版怎么改开头更稳？"),
                ],
            )
            await service.turn(session, payload, owner_id=owner.id)

        prompt = tool_provider.requests[0]["prompt"]
        assert "【当前 Skill 指令】" in prompt
        assert "用户输入：这一版怎么改开头更稳？" in prompt
        assert "【当前会话历史】" in prompt
        assert "用户：上一版太平了。" in prompt
        assert "助手：主要问题是冲突没有持续升级。" in prompt
        assert "【用户当前消息】" not in prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_skill_prompt_appends_missing_history_and_user_input(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_skill_service=skill_service,
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-skill-context-append")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created_skill = await skill_service.create_user_skill(
                session,
                AssistantSkillCreateDTO(
                    name="纯指令 Skill",
                    content="先按冷静、克制的方式回答。",
                ),
                owner_id=owner.id,
            )
            payload = _build_turn_request(
                skill_id=created_skill.id,
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[
                    AssistantMessageDTO(role="user", content="上一版节奏太散。"),
                    AssistantMessageDTO(role="assistant", content="可以先把开头冲突压近一点。"),
                    AssistantMessageDTO(role="user", content="那这一版第一段怎么起？"),
                ],
            )
            await service.turn(session, payload, owner_id=owner.id)

        prompt = tool_provider.requests[0]["prompt"]
        assert "【当前 Skill 指令】" in prompt
        assert "先按冷静、克制的方式回答。" in prompt
        assert "【当前会话历史】" in prompt
        assert "用户：上一版节奏太散。" in prompt
        assert "助手：可以先把开头冲突压近一点。" in prompt
        assert "【用户当前消息】" in prompt
        assert "那这一版第一段怎么起？" in prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_user_after_hook(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    agent_service = AssistantAgentService(
        assistant_skill_service=skill_service,
        config_loader=loader,
        agent_store=AssistantAgentFileStore(tmp_path / "assistant-config"),
    )
    mcp_service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    hook_service = AssistantHookService(
        assistant_agent_service=agent_service,
        assistant_mcp_service=mcp_service,
        config_loader=loader,
        hook_store=AssistantHookFileStore(tmp_path / "assistant-config"),
    )
    service = AssistantService(
        assistant_agent_service=agent_service,
        assistant_hook_service=hook_service,
        assistant_mcp_service=mcp_service,
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_skill_service=skill_service,
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-user-hook")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            created_skill = await skill_service.create_user_skill(
                session,
                AssistantSkillCreateDTO(
                    name="回复整理 Skill",
                    content="请根据以下内容输出一句摘要：\n{{ user_input }}",
                ),
                owner_id=owner_id,
            )
            created_agent = await agent_service.create_user_agent(
                session,
                AssistantAgentCreateDTO(
                    name="回复整理 Agent",
                    skill_id=created_skill.id,
                    system_prompt="你负责把主回复整理成一句摘要。",
                ),
                owner_id=owner_id,
            )
            created_hook = await hook_service.create_user_hook(
                session,
                AssistantHookCreateDTO(
                    name="回复后自动整理",
                    event="after_assistant_response",
                    action={
                        "action_type": "agent",
                        "agent_id": created_agent.id,
                    },
                ),
                owner_id=owner_id,
            )
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                hook_ids=[created_hook.id],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.content.startswith("主回复：")
        assert [item.model_dump(mode="json") for item in response.hook_results] == [
            {
                "event": "after_assistant_response",
                "hook_id": created_hook.id,
                "action_type": "agent",
                "result": "Hook 摘要完成。",
            }
        ]
        assert len(tool_provider.requests) == 2
        assert tool_provider.requests[1]["model"] == tool_provider.requests[0]["model"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_user_mcp_hook(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    mcp_tool_caller = _FakeMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    agent_service = AssistantAgentService(
        assistant_skill_service=skill_service,
        config_loader=loader,
        agent_store=AssistantAgentFileStore(tmp_path / "assistant-config"),
    )
    mcp_service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    hook_service = AssistantHookService(
        assistant_agent_service=agent_service,
        assistant_mcp_service=mcp_service,
        config_loader=loader,
        hook_store=AssistantHookFileStore(tmp_path / "assistant-config"),
    )
    service = AssistantService(
        assistant_agent_service=agent_service,
        assistant_hook_service=hook_service,
        assistant_mcp_service=mcp_service,
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_skill_service=skill_service,
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        mcp_server_resolver=lambda context, server_id: mcp_service.resolve_mcp_server(
            server_id,
            owner_id=context.owner_id,
        ),
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-user-mcp-hook")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            created_mcp = await mcp_service.create_user_mcp_server(
                session,
                AssistantMcpCreateDTO(
                    name="新闻查询",
                    url="https://example.com/user-mcp",
                    headers={"X-Test": "demo"},
                ),
                owner_id=owner_id,
            )
            created_hook = await hook_service.create_user_hook(
                session,
                AssistantHookCreateDTO(
                    name="回复前查新闻",
                    event="before_assistant_response",
                    action={
                        "action_type": "mcp",
                        "server_id": created_mcp.id,
                        "tool_name": "search_news",
                        "arguments": {"limit": 3},
                        "input_mapping": {"query": "request.user_input"},
                    },
                ),
                owner_id=owner_id,
            )
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                hook_ids=[created_hook.id],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.mcp_servers == []
        assert response.hook_results[0].action_type == "mcp"
        assert mcp_tool_caller.calls == [
            (created_mcp.id, "search_news", {"limit": 3, "query": "今天有什么新闻？"})
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_project_read_documents_tool_loop(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ToolCallingFakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(
        project.id,
        "设定/人物.md",
        "# 人物\n\n林渊：冷静、克制，擅长从细枝末节里发现异常。",
    )
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="先读一下人物设定，再给我一个悬疑开场方向。")],
    )
    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert response.content.startswith("我已经读完人物设定")
    assert [item.item_type for item in response.output_items] == ["tool_call", "tool_result", "text"]
    assert response.output_items[0].call_id == "call.project.read_documents.1"
    assert response.output_items[1].payload["structured_output"]["documents"][0]["path"] == "设定/人物.md"
    assert response.total_tokens == 54
    assert [item["name"] for item in tool_provider.requests[0]["tools"]] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
    ]
    assert tool_provider.requests[1]["prompt"] == tool_provider.requests[0]["prompt"]
    assert _request_contains_continuation_fragment(
        tool_provider.requests[1],
        "设定/人物.md",
    )
    assert _request_contains_continuation_fragment(
        tool_provider.requests[1],
        "林渊",
    )
    assert tool_provider.requests[1]["provider_continuation_state"] == {
        "previous_response_id": "resp_tool_1",
        "latest_items": tool_provider.requests[1]["continuation_items"],
    }
    step_history = step_store.list_step_history(response.run_id, "call.project.read_documents.1")
    run_record = turn_run_store.get_run(response.run_id)
    assert [item.status for item in step_history] == ["reading", "completed"]
    assert step_history[-1].tool_name == "project.read_documents"
    assert step_history[-1].target_document_refs[0].startswith("project_file:")
    assert step_history[-1].result_summary == {
        "content_item_count": 1,
        "document_count": 1,
        "paths": ["设定/人物.md"],
        "resource_count": 1,
    }
    assert run_record is not None
    assert run_record.status == "completed"
    assert run_record.requested_write_scope == "disabled"
    assert run_record.requested_write_targets_snapshot == ()
    assert run_record.exposed_tool_names_snapshot == (
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
    )
    assert [item["name"] for item in run_record.resolved_tool_descriptor_snapshot] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
    ]
    assert run_record.budget_snapshot == _expected_run_budget(max_steps=8, tool_timeout_seconds=15)
    assert run_record.continuation_request_snapshot == {
        "continuation_items": tool_provider.requests[1]["continuation_items"],
        "provider_continuation_state": tool_provider.requests[1]["provider_continuation_state"],
    }
    assert run_record.provider_continuation_state == {
        "previous_response_id": "resp_tool_1",
        "latest_items": tool_provider.requests[1]["continuation_items"],
    }
    assert run_record.pending_tool_calls_snapshot == ()
    assert run_record.state_version >= 4
    assert run_record.started_at <= run_record.updated_at
    assert run_record.completed_at is not None
    assert run_record.updated_at <= run_record.completed_at
    policy_by_name = {
        item["descriptor"]["name"]: item
        for item in run_record.tool_policy_decisions_snapshot
    }
    assert policy_by_name["project.list_documents"]["visibility"] == "visible"
    assert policy_by_name["project.search_documents"]["visibility"] == "visible"
    assert policy_by_name["project.read_documents"]["visibility"] == "visible"
    assert policy_by_name["project.read_documents"]["effective_approval_mode"] == "none"
    assert policy_by_name["project.write_document"]["visibility"] == "hidden"
    assert policy_by_name["project.write_document"]["hidden_reason"] == "write_grant_unavailable"
    assert run_record.document_context_snapshot is None
    assert run_record.document_context_recovery_snapshot is None
    assert run_record.turn_context_hash
    assert [item["item_type"] for item in run_record.normalized_input_items_snapshot] == [
        "message",
        "model_selection",
        "tool_call",
        "tool_result",
        "message",
    ]


async def test_assistant_service_allows_project_tools_without_verified_credential(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ToolCallingFakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_TextOnlyCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=AssistantToolStepStore(tmp_path / "tool-steps"),
        ),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(
        project.id,
        "设定/人物.md",
        "# 人物\n\n林渊：冷静、克制，擅长从细枝末节里发现异常。",
    )
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="先读一下人物设定，再给我一个悬疑开场方向。")],
    )

    result = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert "林渊" in result.content
    assert len(tool_provider.requests) == 2


async def test_assistant_service_persists_continuation_compaction_snapshot_for_tool_loop(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ToolCallingCompactionProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_ToolLoopCompactingCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    long_document = "# 人物\n\n林渊：冷静、克制，擅长从细枝末节里发现异常。\n\n" + (
        "他会先看脚印、气味和雨声的微妙变化，再判断危险来自哪里。 " * 500
    )
    file_store.save_project_document(project.id, "设定/人物.md", long_document)
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="先读一下人物设定，再给我一个悬疑开场方向。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    run_record = turn_run_store.get_run(response.run_id)

    assert response.content.startswith("我已经读完人物设定")
    assert run_record is not None
    assert run_record.budget_snapshot == _expected_run_budget(
        max_steps=8,
        tool_timeout_seconds=15,
        max_input_tokens=1600,
    )
    assert run_record.continuation_compaction_snapshot is not None
    assert run_record.continuation_compaction_snapshot["phase"] == "tool_loop_continuation"
    assert run_record.continuation_compaction_snapshot["level"] == "hard"
    assert run_record.continuation_compaction_snapshot["estimated_tokens_before"] > (
        run_record.continuation_compaction_snapshot["estimated_tokens_after"]
    )
    assert run_record.continuation_compaction_snapshot["compacted_tool_names"] == [
        "project.read_documents"
    ]
    continuation_document_ref = tool_provider.requests[1]["continuation_items"][1]["payload"][
        "structured_output"
    ]["documents"][0]["document_ref"]
    continuation_document_version = tool_provider.requests[1]["continuation_items"][1]["payload"][
        "structured_output"
    ]["documents"][0]["version"]
    continuation_catalog_version = tool_provider.requests[1]["continuation_items"][1]["payload"][
        "structured_output"
    ]["catalog_version"]
    assert run_record.continuation_compaction_snapshot["compacted_document_refs"] == [
        continuation_document_ref
    ]
    assert run_record.continuation_compaction_snapshot["compacted_document_versions"] == {
        continuation_document_ref: continuation_document_version
    }
    assert run_record.continuation_compaction_snapshot["compacted_catalog_versions"] == [
        continuation_catalog_version
    ]
    assert run_record.continuation_compaction_snapshot["compressed_items_digest"]
    assert run_record.continuation_compaction_snapshot["projected_items_digest"] == (
        build_structured_items_digest(
            run_record.continuation_request_snapshot["continuation_items"]
        )
    )
    assert (
        run_record.continuation_compaction_snapshot["compressed_items_digest"]
        != run_record.continuation_compaction_snapshot["projected_items_digest"]
    )
    assert run_record.continuation_compaction_snapshot["trimmed_text_slot_count"] >= 1
    assert run_record.continuation_compaction_snapshot["dropped_content_item_count"] >= 1
    assert run_record.continuation_request_snapshot == {
        "continuation_items": tool_provider.requests[1]["continuation_items"],
        "provider_continuation_state": tool_provider.requests[1]["provider_continuation_state"],
    }
    assert run_record.provider_continuation_state is not None
    assert run_record.provider_continuation_state["previous_response_id"] == "resp_tool_1"
    assert tool_provider.requests[1]["provider_continuation_state"] == {
        "previous_response_id": "resp_tool_1",
        "latest_items": tool_provider.requests[1]["continuation_items"],
    }


async def test_assistant_service_persists_and_validates_continuation_anchor(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-continuation")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            first_payload = _build_turn_request(
                messages=[AssistantMessageDTO(role="user", content="先给我一个方向。")],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            first_response = await service.turn(session, first_payload, owner_id=owner_id)

            second_payload = _build_turn_request(
                continuation_anchor=AssistantContinuationAnchorDTO(
                    previous_run_id=first_response.run_id,
                ),
                messages=[
                    AssistantMessageDTO(role="user", content="先给我一个方向。"),
                    AssistantMessageDTO(role="assistant", content=first_response.content),
                    AssistantMessageDTO(role="user", content="继续往下展开。"),
                ],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            second_response = await service.turn(session, second_payload, owner_id=owner_id)

            mismatched_payload = _build_turn_request(
                continuation_anchor=AssistantContinuationAnchorDTO(
                    previous_run_id=first_response.run_id,
                ),
                messages=[
                    AssistantMessageDTO(role="user", content="先给我一个方向。"),
                    AssistantMessageDTO(role="assistant", content="被篡改的上一轮回复"),
                    AssistantMessageDTO(role="user", content="继续往下展开。"),
                ],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            with pytest.raises(BusinessRuleError) as exc_info:
                await service.turn(session, mismatched_payload, owner_id=owner_id)

            third_parent_messages = [
                AssistantMessageDTO(role="user", content="先给我一个方向。"),
                AssistantMessageDTO(role="assistant", content=first_response.content),
                AssistantMessageDTO(role="user", content="继续往下展开。"),
                AssistantMessageDTO(role="assistant", content=second_response.content),
            ]
            third_payload = _build_turn_request(
                continuation_anchor=AssistantContinuationAnchorDTO(
                    previous_run_id=second_response.run_id,
                    messages_digest=build_turn_messages_digest(third_parent_messages),
                ),
                messages=[
                    *third_parent_messages,
                    AssistantMessageDTO(role="user", content="把第三段再压成一句话。"),
                ],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            third_response = await service.turn(session, third_payload, owner_id=owner_id)

        first_run = turn_run_store.get_run(first_response.run_id)
        second_run = turn_run_store.get_run(second_response.run_id)
        third_run = turn_run_store.get_run(third_response.run_id)
        second_parent_digest = build_turn_messages_digest(second_payload.messages[:-1])

        assert exc_info.value.code == "conversation_state_mismatch"
        assert str(exc_info.value) == "当前会话状态已变化，请刷新对话后重试。"
        assert second_response.content.startswith("主回复：")
        assert first_run is not None
        assert second_run is not None
        assert third_run is not None
        assert first_run.terminal_status == "completed"
        assert second_run.terminal_status == "completed"
        assert third_run.terminal_status == "completed"
        assert first_run.continuation_anchor_snapshot is None
        assert second_run.continuation_anchor_snapshot == {
            "previous_run_id": str(first_response.run_id),
            "messages_digest": second_parent_digest,
        }
        assert third_run.continuation_anchor_snapshot == {
            "previous_run_id": str(second_response.run_id),
            "messages_digest": build_turn_messages_digest(third_payload.messages[:-1]),
        }
        assert second_run.requested_write_scope == "disabled"
        assert second_run.exposed_tool_names_snapshot == ()
        assert second_run.tool_policy_decisions_snapshot == ()
        assert second_run.budget_snapshot is None
        assert [item["item_type"] for item in second_run.normalized_input_items_snapshot] == [
            "message",
            "message",
            "message",
            "model_selection",
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_replays_completed_turn_for_same_client_turn_id(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-idempotent-completed")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                messages=[AssistantMessageDTO(role="user", content="先给我一个方向。")],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            first_response = await service.turn(session, payload, owner_id=owner_id)
            second_response = await service.turn(session, payload, owner_id=owner_id)

            assert second_response == first_response
            assert len(tool_provider.requests) == 1

            conflicting_payload = payload.model_copy(
                update={
                    "messages": [
                        AssistantMessageDTO(role="user", content="换一个完全不同的问题。"),
                    ]
                }
            )
            with pytest.raises(BusinessRuleError) as exc_info:
                await service.turn(session, conflicting_payload, owner_id=owner_id)

            assert exc_info.value.code == "turn_idempotency_conflict"

            conflicting_model_payload = AssistantTurnRequestDTO.model_validate(
                {
                    **payload.model_dump(mode="json"),
                    "model": {"provider": "openai", "name": "gpt-5"},
                }
            )
            with pytest.raises(BusinessRuleError) as model_exc_info:
                await service.turn(session, conflicting_model_payload, owner_id=owner_id)

            assert model_exc_info.value.code == "turn_idempotency_conflict"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_compacts_history_and_preserves_relation_anchors(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_CompactingCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
        project_document_capability_service=capability_service,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(project.id, "数据层/人物关系.json", '{"relations":["林渊-顾砚：互相试探"]}')
    file_store.save_project_document(project.id, "数据层/势力关系.json", '{"relations":["黑潮会-白塔局：长期对抗"]}')
    file_store.save_project_document(project.id, "设定/伏笔.md", "第一卷要埋下黑潮会真实目标的伏笔。")
    payload = _build_turn_request(
        project_id=project.id,
        skill_id="skill.assistant.general_chat",
        model={"provider": "openai", "name": "gpt-4o-mini", "max_tokens": 64},
        document_context={
            "selected_paths": [
                "数据层/人物关系.json",
                "数据层/势力关系.json",
                "设定/伏笔.md",
            ]
        },
        messages=[
            AssistantMessageDTO(
                role="user",
                content="人物关系里林渊和顾砚的互相试探必须贯穿全文，不能写成前几章提过后面就消失。",
            ),
            AssistantMessageDTO(
                role="assistant",
                content="我会把这条人物关系保持成持续施压的暗线，让两人的试探不断影响表面合作。",
            ),
            AssistantMessageDTO(
                role="user",
                content="势力关系也不能丢，黑潮会和白塔局的长期对抗是主线压力源，时间轴必须能对上。",
            ),
            AssistantMessageDTO(
                role="assistant",
                content="已记录：人物关系、势力关系、伏笔回收和时间轴一致性都要贯穿全文，尤其第一卷不能掉线。",
            ),
            AssistantMessageDTO(role="user", content="基于这些约束，给我一个冷峻克制的开篇第一场戏方向。"),
        ],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    prompt = tool_provider.requests[0]["prompt"]
    run_record = turn_run_store.get_run(response.run_id)

    assert "【压缩后的早期对话摘要】" in prompt
    assert response.content.startswith("主回复：")
    assert run_record is not None
    assert run_record.compaction_snapshot is not None
    assert run_record.budget_snapshot is not None
    assert run_record.budget_snapshot["max_steps"] == 1
    assert run_record.budget_snapshot["max_tool_calls"] is None
    assert run_record.budget_snapshot["max_input_tokens"] == 216
    assert run_record.budget_snapshot["tool_timeout_seconds"] is None
    assert run_record.compaction_snapshot["phase"] == "initial_prompt"
    assert run_record.compaction_snapshot["level"] == "soft"
    history_messages = payload.messages[:-1]
    preserved_recent_count = run_record.compaction_snapshot["preserved_recent_message_count"]
    compacted_messages = (
        history_messages[:-preserved_recent_count]
        if preserved_recent_count > 0
        else history_messages
    )
    projected_messages = (
        [*history_messages[-preserved_recent_count:], payload.messages[-1]]
        if preserved_recent_count > 0
        else [payload.messages[-1]]
    )
    assert run_record.compaction_snapshot["compressed_messages_digest"] == build_turn_messages_digest(
        compacted_messages
    )
    assert run_record.compaction_snapshot["projected_messages_digest"] == build_turn_messages_digest(
        projected_messages
    )
    assert "数据层/人物关系.json" in run_record.compaction_snapshot["protected_document_paths"]
    assert "数据层/势力关系.json" in run_record.compaction_snapshot["protected_document_paths"]
    assert set(run_record.compaction_snapshot["protected_document_refs"]) == {
        binding["document_ref"]
        for binding in run_record.document_context_bindings_snapshot
        if binding["path"] in run_record.compaction_snapshot["protected_document_paths"]
    }
    assert set(run_record.compaction_snapshot["protected_document_reasons"]["数据层/人物关系.json"]) >= {
        "selected_path",
        "binding",
        "data_layer_path",
    }
    assert set(run_record.compaction_snapshot["protected_document_reasons"]["数据层/势力关系.json"]) >= {
        "selected_path",
        "binding",
        "data_layer_path",
    }
    assert run_record.compaction_snapshot["protected_document_binding_versions"] == {
        binding["document_ref"]: binding["binding_version"]
        for binding in run_record.document_context_bindings_snapshot
        if (
            binding["path"] in run_record.compaction_snapshot["protected_document_paths"]
            and binding.get("binding_version")
        )
    }
    assert run_record.compaction_snapshot["document_context_collapsed"] is False
    assert run_record.compaction_snapshot["document_context_projection_mode"] == "selected_only"
    assert run_record.document_context_snapshot is not None
    assert run_record.document_context_injection_snapshot is not None
    assert (
        run_record.compaction_snapshot["projected_document_context_snapshot"]
        == run_record.document_context_injection_snapshot
    )
    assert (
        run_record.compaction_snapshot["document_context_recovery_snapshot"]
        == run_record.document_context_recovery_snapshot
    )
    assert set(run_record.compaction_snapshot["summary_anchor_keywords"]) >= {
        "人物关系",
        "势力关系",
        "贯穿全文",
    }
    assert "人物关系" in run_record.compaction_snapshot["summary"]
    assert "势力关系" in run_record.compaction_snapshot["summary"]
    assert "贯穿全文" in run_record.compaction_snapshot["summary"]
    compacted_item = next(
        item
        for item in run_record.normalized_input_items_snapshot
        if item["item_type"] == "compacted_context"
    )
    assert compacted_item["content"] == run_record.compaction_snapshot["summary"]
    assert compacted_item["payload"] == run_record.compaction_snapshot
    assert compacted_item["payload"]["phase"] == "initial_prompt"
    assert compacted_item["payload"]["level"] == "soft"
    assert compacted_item["payload"]["budget_limit_tokens"] == 216
    assert (
        compacted_item["payload"]["compressed_messages_digest"]
        == run_record.compaction_snapshot["compressed_messages_digest"]
    )
    assert (
        compacted_item["payload"]["projected_messages_digest"]
        == run_record.compaction_snapshot["projected_messages_digest"]
    )
    assert (
        compacted_item["payload"]["summary_anchor_keywords"]
        == run_record.compaction_snapshot["summary_anchor_keywords"]
    )
    assert (
        compacted_item["payload"]["protected_document_reasons"]
        == run_record.compaction_snapshot["protected_document_reasons"]
    )
    assert (
        compacted_item["payload"]["protected_document_binding_versions"]
        == run_record.compaction_snapshot["protected_document_binding_versions"]
    )
    assert (
        compacted_item["payload"]["document_context_recovery_snapshot"]
        == run_record.document_context_recovery_snapshot
    )
    assert (
        compacted_item["payload"]["projected_document_context_snapshot"]
        == run_record.compaction_snapshot["projected_document_context_snapshot"]
    )
    assert (
        compacted_item["payload"]["document_context_projection_mode"]
        == run_record.compaction_snapshot["document_context_projection_mode"]
    )


async def test_assistant_prepare_turn_exposes_compaction_snapshot_in_hook_payload(
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_CompactingCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-hook-context-snapshots")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            payload = _build_turn_request(
                project_id=project.id,
                skill_id="skill.assistant.general_chat",
                model={"provider": "openai", "name": "gpt-4o-mini", "max_tokens": 32},
                messages=[
                    AssistantMessageDTO(
                        role="user",
                        content="人物关系里林渊和顾砚的互相试探必须贯穿全文，时间轴也不能乱。 " * 3,
                    ),
                    AssistantMessageDTO(
                        role="assistant",
                        content="我会把人物关系和时间轴都维持成贯穿全文的连续性压力。 " * 3,
                    ),
                    AssistantMessageDTO(
                        role="user",
                        content="黑潮会和白塔局的长期对抗也要保留，不能只在前期出现。 " * 3,
                    ),
                    AssistantMessageDTO(
                        role="assistant",
                        content="已记录：人物关系、势力关系与时间轴一致性都不能掉线。 " * 3,
                    ),
                    AssistantMessageDTO(
                        role="user",
                        content="基于这些约束，给我一个冷峻克制的开篇方向。人物关系、势力关系和时间轴都要继续有效。 " * 2,
                    ),
                ],
            )

            prepared = await service._prepare_turn(session, payload, owner_id=owner.id)  # noqa: SLF001
            assert prepared.turn_context.compaction_snapshot is not None
            assert (
                prepared.before_payload["request"]["compaction_snapshot"]
                == prepared.turn_context.compaction_snapshot
            )
            assert prepared.before_payload["request"]["tool_guidance_snapshot"] is None
            assert (
                prepared.before_payload["request"]["tool_catalog_version"]
                == prepared.turn_context.tool_catalog_version
            )
            assert prepared.before_payload["request"]["exposed_tool_names_snapshot"] == []

            after_payload = build_after_assistant_payload(
                prepared.spec,
                payload,
                prepared.project_id,
                prepared.turn_context,
                "主回复：给出方向。",
                visible_tool_descriptors=prepared.visible_tool_descriptors,
            )
            assert (
                after_payload["request"]["compaction_snapshot"]
                == prepared.turn_context.compaction_snapshot
            )
            assert after_payload["request"]["tool_guidance_snapshot"] is None
            assert (
                after_payload["request"]["tool_catalog_version"]
                == prepared.turn_context.tool_catalog_version
            )
            assert after_payload["request"]["exposed_tool_names_snapshot"] == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_prepare_turn_exposes_tool_guidance_snapshot_in_hook_payload_when_visible_tools_match(
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
        ),
        project_document_capability_service=capability_service,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-hook-tool-guidance-snapshot")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            payload = _build_turn_request(
                project_id=project.id,
                skill_id="skill.assistant.general_chat",
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[
                    AssistantMessageDTO(
                        role="user",
                        content="人物关系和时间轴的一致性要贯穿全文，先告诉我应该查哪些资料。",
                    )
                ],
            )

            prepared = await service._prepare_turn(session, payload, owner_id=owner.id)  # noqa: SLF001

            assert prepared.turn_context.tool_guidance_snapshot is not None
            assert (
                prepared.before_payload["request"]["tool_guidance_snapshot"]
                == prepared.turn_context.tool_guidance_snapshot
            )
            assert (
                prepared.before_payload["request"]["tool_catalog_version"]
                == prepared.turn_context.tool_catalog_version
            )
            assert prepared.before_payload["request"]["exposed_tool_names_snapshot"] == [
                item.name for item in prepared.visible_tool_descriptors
            ]

            after_payload = build_after_assistant_payload(
                prepared.spec,
                payload,
                prepared.project_id,
                prepared.turn_context,
                "主回复：先查人物关系和时间轴相关文稿。",
                visible_tool_descriptors=prepared.visible_tool_descriptors,
            )
            assert (
                after_payload["request"]["tool_guidance_snapshot"]
                == prepared.turn_context.tool_guidance_snapshot
            )
            assert (
                after_payload["request"]["tool_catalog_version"]
                == prepared.turn_context.tool_catalog_version
            )
            assert after_payload["request"]["exposed_tool_names_snapshot"] == [
                item.name for item in prepared.visible_tool_descriptors
            ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_prepare_turn_exposes_document_context_recovery_snapshot_in_hook_payload(
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        project_document_capability_service=capability_service,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-hook-document-context-recovery")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            file_store.save_project_document(project.id, "设定/人物.md", "林渊：冷静克制，擅长观察。")
        async with async_session_factory() as session:
            payload = _build_turn_request(
                project_id=project.id,
                skill_id="skill.assistant.general_chat",
                model={"provider": "openai", "name": "gpt-4o-mini"},
                document_context={
                    "active_path": "设定/人物.md",
                    "selected_paths": ["设定/人物.md"],
                    "active_buffer_state": {
                        "dirty": True,
                        "base_version": "version:v1",
                        "buffer_hash": "buffer:abc",
                        "source": TRUSTED_ACTIVE_BUFFER_SOURCE,
                    },
                },
                messages=[AssistantMessageDTO(role="user", content="继续沿人物设定往下写。")],
            )

            prepared = await service._prepare_turn(session, payload, owner_id=owner.id)  # noqa: SLF001
            assert prepared.turn_context.document_context_recovery_snapshot is not None
            assert prepared.turn_context.document_context_injection_snapshot is not None
            assert (
                prepared.run_snapshot.document_context_injection_snapshot
                == prepared.turn_context.document_context_injection_snapshot
            )
            assert (
                prepared.before_payload["request"]["document_context_bindings_snapshot"]
                == prepared.turn_context.document_context_bindings
            )
            assert (
                prepared.before_payload["request"]["document_context_recovery_snapshot"]
                == prepared.turn_context.document_context_recovery_snapshot
            )
            assert (
                prepared.before_payload["request"]["document_context_injection_snapshot"]
                == prepared.turn_context.document_context_injection_snapshot
            )

            after_payload = build_after_assistant_payload(
                prepared.spec,
                payload,
                prepared.project_id,
                prepared.turn_context,
                "主回复：继续写。",
                visible_tool_descriptors=prepared.visible_tool_descriptors,
            )
            assert (
                after_payload["request"]["document_context_bindings_snapshot"]
                == prepared.turn_context.document_context_bindings
            )
            assert (
                after_payload["request"]["document_context_recovery_snapshot"]
                == prepared.turn_context.document_context_recovery_snapshot
            )
            assert (
                after_payload["request"]["document_context_injection_snapshot"]
                == prepared.turn_context.document_context_injection_snapshot
            )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def test_build_request_error_hook_payload_keeps_bindings_snapshot_shape_stable() -> None:
    owner_id = uuid.uuid4()
    payload = AssistantTurnRequestDTO(
        conversation_id="conversation-on-error-bindings",
        client_turn_id="turn-on-error-bindings",
        messages=[AssistantMessageDTO(role="user", content="继续往下写。")],
        document_context={
            "active_path": "设定/人物.md",
            "selected_paths": ["设定/人物.md"],
        },
        model={"provider": "openai", "name": "gpt-4o-mini"},
    )

    hook_payload = build_request_error_hook_payload(payload=payload, owner_id=owner_id)

    assert hook_payload["request"]["document_context"] == payload.document_context.model_dump(mode="json")
    assert hook_payload["request"]["document_context_bindings_snapshot"] is None
    assert hook_payload["request"]["document_context_recovery_snapshot"] is None
    assert hook_payload["request"]["document_context_injection_snapshot"] == (
        build_document_context_injection_snapshot(
            payload.document_context.model_dump(mode="json")
        )
    )
    assert hook_payload["request"]["tool_catalog_version"] is None
    assert hook_payload["request"]["exposed_tool_names_snapshot"] == []


async def test_assistant_prepare_turn_records_project_tool_guidance_as_explicit_snapshot(
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
        ),
        turn_run_store=turn_run_store,
        project_document_capability_service=capability_service,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-tool-guidance")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            payload = _build_turn_request(
                project_id=project.id,
                messages=[
                    AssistantMessageDTO(
                        role="user",
                        content="这段人物关系和时间轴的一致性要贯穿全文，你先帮我判断应该查哪些资料。",
                    )
                ],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )

            prepared = await service._prepare_turn(session, payload, owner_id=owner.id)  # noqa: SLF001

            assert "【项目范围工具提示】" in prepared.prompt
            tool_guidance = next(
                item
                for item in prepared.turn_context.normalized_input_items
                if item["item_type"] == "tool_guidance"
            )
            assert tool_guidance["payload"]["guidance_type"] == "project_search_then_read"
            assert tool_guidance["payload"]["tool_names"] == [
                "project.search_documents",
                "project.read_documents",
            ]
            assert tool_guidance["payload"]["discovery_source"] == "continuity_keywords"
            assert "人物关系" in tool_guidance["payload"]["trigger_keywords"]
            assert "时间轴" in tool_guidance["payload"]["trigger_keywords"]
            assert prepared.turn_context.tool_guidance_snapshot is not None
            assert tool_guidance["payload"]["content"].startswith("【项目范围工具提示】")
            assert prepared.turn_context.tool_guidance_snapshot["content"] in prepared.prompt
            assert prepared.turn_context.tool_guidance_snapshot == tool_guidance["payload"]
            assert prepared.run_snapshot.tool_guidance_snapshot == tool_guidance["payload"]

            response = await service.turn(session, payload, owner_id=owner.id)

            run_record = turn_run_store.get_run(response.run_id)
            assert run_record is not None
            assert run_record.tool_guidance_snapshot == tool_guidance["payload"]
            stored_tool_guidance = next(
                item
                for item in run_record.normalized_input_items_snapshot
                if item["item_type"] == "tool_guidance"
            )
            assert stored_tool_guidance["payload"] == run_record.tool_guidance_snapshot
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_prepare_turn_omits_project_tool_guidance_without_visible_project_tools(
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-tool-guidance-without-visible-tools")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            payload = _build_turn_request(
                project_id=project.id,
                messages=[
                    AssistantMessageDTO(
                        role="user",
                        content="这段人物关系和时间轴的一致性要贯穿全文，你先帮我判断应该查哪些资料。",
                    )
                ],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )

            prepared = await service._prepare_turn(session, payload, owner_id=owner.id)  # noqa: SLF001

            assert "【项目范围工具提示】" not in prepared.prompt
            assert prepared.turn_context.tool_guidance_snapshot is None
            assert prepared.run_snapshot.tool_guidance_snapshot is None
            assert prepared.visible_tool_descriptors == ()
            assert all(
                item["item_type"] != "tool_guidance"
                for item in prepared.turn_context.normalized_input_items
            )

            response = await service.turn(session, payload, owner_id=owner.id)

            run_record = turn_run_store.get_run(response.run_id)
            assert run_record is not None
            assert run_record.tool_guidance_snapshot is None
            assert all(
                item["item_type"] != "tool_guidance"
                for item in run_record.normalized_input_items_snapshot
            )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_raises_budget_exhausted_when_latest_message_alone_exceeds_budget(
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_CompactingCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-budget-exhausted")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        huge_message = "人物关系、势力关系和贯穿全文的主线都不能丢。 " * 40
        async with async_session_factory() as session:
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                model={"provider": "openai", "name": "gpt-4o-mini", "max_tokens": 64},
                messages=[AssistantMessageDTO(role="user", content=huge_message)],
            )
            with pytest.raises(BusinessRuleError) as exc_info:
                await service.turn(session, payload, owner_id=owner_id)

        run_id = build_turn_run_id(
            owner_id=owner_id,
            project_id=None,
            conversation_id=payload.conversation_id,
            client_turn_id=payload.client_turn_id,
        )
        assert exc_info.value.code == "budget_exhausted"
        assert turn_run_store.get_run(run_id) is None
        assert tool_provider.requests == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_uses_context_window_without_implicit_max_tokens(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_CompactingCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-implicit-max-tokens")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                messages=[AssistantMessageDTO(role="user", content="用一句话概括当前剧情核心冲突。")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        run_record = turn_run_store.get_run(response.run_id)
        assert response.content.startswith("主回复：")
        assert run_record is not None
        assert run_record.budget_snapshot is not None
        assert run_record.budget_snapshot["max_input_tokens"] == 280
        assert "max_tokens" not in tool_provider.requests[0]["model"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_replays_completed_recoverable_tool_turn_for_same_client_turn_id(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _WriteConflictToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    current_content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    payload = _build_turn_request(
        project_id=project.id,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version="sha256:stale",
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="尝试覆盖旧版本人物设定。")],
    )

    first_response = await service.turn(async_db(db), payload, owner_id=owner.id)
    replay_response = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert replay_response == first_response
    assert replay_response.content.startswith("写回失败，因为人物设定已经有新版本")
    assert len(tool_provider.requests) == 2


async def test_assistant_service_blocks_reentry_for_running_turn(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-running-turn")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                messages=[AssistantMessageDTO(role="user", content="先给我一个方向。")],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            prepared = await service._prepare_turn(session, payload, owner_id=owner_id)  # noqa: SLF001
            assert turn_run_store.create_run(
                service._build_running_turn_record(prepared, owner_id=owner_id)  # noqa: SLF001
            )

            with pytest.raises(BusinessRuleError) as exc_info:
                await service.turn(session, payload, owner_id=owner_id)

            assert exc_info.value.code == "run_in_progress"
            assert len(tool_provider.requests) == 0
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_marks_stale_running_turn_failed_without_replay(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "app.modules.assistant.service.assistant_runtime_claim_support._is_process_alive",
        lambda pid: False,
    )
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-stale-running-turn")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                messages=[AssistantMessageDTO(role="user", content="这次继续聊剧情方向。")],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            prepared = await service._prepare_turn(session, payload, owner_id=owner_id)  # noqa: SLF001
            stale_claim = {
                "host": service.runtime_claim_snapshot["host"],
                "instance_id": "stale-runtime",
                "pid": 999999,
            }
            assert turn_run_store.create_run(
                service._build_running_turn_record(  # noqa: SLF001
                    prepared,
                    owner_id=owner_id,
                    runtime_claim_snapshot=stale_claim,
                )
            )

            with pytest.raises(BusinessRuleError) as exc_info:
                await service.turn(session, payload, owner_id=owner_id)

            assert exc_info.value.code == "stale_run_interrupted"
            assert tool_provider.requests == []
            run_record = turn_run_store.get_run(prepared.turn_context.run_id)
            assert run_record is not None
            assert run_record.status == "failed"
            assert run_record.terminal_error_code == "stale_run_interrupted"
            assert run_record.write_effective is False
            assert run_record.completed_at is not None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_preserves_existing_running_turn_snapshot_truth_when_stale_run_is_terminated(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "app.modules.assistant.service.assistant_runtime_claim_support._is_process_alive",
        lambda pid: False,
    )
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
        project_document_capability_service=capability_service,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-stale-running-turn-truth")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        current_content = "# 人物\n\n林渊"
        file_store.save_project_document(project.id, "设定/人物.md", current_content)
        async with async_session_factory() as session:
            payload = _build_turn_request(
                project_id=project.id,
                messages=[AssistantMessageDTO(role="user", content="这次继续聊剧情方向。")],
                document_context={
                    "active_path": "设定/人物.md",
                    "active_buffer_state": _build_trusted_active_buffer_state(
                        base_version="sha256:base",
                        content=current_content,
                    ),
                },
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            prepared = await service._prepare_turn(session, payload, owner_id=owner.id)  # noqa: SLF001
            assert prepared.turn_context.tool_catalog_version is not None
            assert prepared.turn_context.tool_catalog_version.startswith("tool_catalog:")
            assert prepared.run_snapshot.tool_catalog_version == prepared.turn_context.tool_catalog_version
            stale_claim = {
                "host": service.runtime_claim_snapshot["host"],
                "instance_id": "stale-runtime",
                "pid": 999999,
            }
            stale_run = dataclasses.replace(
                service._build_running_turn_record(  # noqa: SLF001
                    prepared,
                    owner_id=owner.id,
                    runtime_claim_snapshot=stale_claim,
                ),
                tool_catalog_version="tool_catalog:existing-run",
            )
            assert turn_run_store.create_run(stale_run)
            stored_run = turn_run_store.get_run(prepared.turn_context.run_id)
            assert stored_run is not None
            assert stored_run.tool_catalog_version == "tool_catalog:existing-run"

            with pytest.raises(BusinessRuleError) as exc_info:
                await service.turn(session, payload, owner_id=owner.id)

            assert exc_info.value.code == "stale_run_interrupted"
            assert tool_provider.requests == []
            run_record = turn_run_store.get_run(prepared.turn_context.run_id)
            assert run_record is not None
            assert run_record.status == "failed"
            assert run_record.terminal_error_code == "stale_run_interrupted"
            assert run_record.tool_catalog_version == "tool_catalog:existing-run"
            assert run_record.write_effective is False
            assert run_record.completed_at is not None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_marks_stale_written_running_turn_failed_without_replay(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "app.modules.assistant.service.assistant_runtime_claim_support._is_process_alive",
        lambda pid: False,
    )
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-stale-written-running-turn")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                messages=[AssistantMessageDTO(role="user", content="继续给我一个剧情建议。")],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )
            prepared = await service._prepare_turn(session, payload, owner_id=owner_id)  # noqa: SLF001
            stale_claim = {
                "host": service.runtime_claim_snapshot["host"],
                "instance_id": "stale-runtime",
                "pid": 999999,
            }
            assert turn_run_store.create_run(
                service._build_running_turn_record(  # noqa: SLF001
                    prepared,
                    owner_id=owner_id,
                    write_effective=True,
                    runtime_claim_snapshot=stale_claim,
                )
            )

            with pytest.raises(BusinessRuleError) as exc_info:
                await service.turn(session, payload, owner_id=owner_id)

            assert exc_info.value.code == "stale_run_write_state_unknown"
            assert tool_provider.requests == []
            run_record = turn_run_store.get_run(prepared.turn_context.run_id)
            assert run_record is not None
            assert run_record.status == "failed"
            assert run_record.terminal_error_code == "stale_run_write_state_unknown"
            assert run_record.write_effective is True
            assert run_record.completed_at is not None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def test_assistant_turn_run_store_rejects_invalid_requested_write_scope(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-scope",
            "client_turn_id": "turn-invalid-scope-1",
            "continuation_anchor_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "session",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "turn_context_hash": "0" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="requested_write_scope"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_normalized_input_item_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-input-item",
            "client_turn_id": "turn-invalid-input-item-1",
            "continuation_anchor_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "turn_context_hash": "1" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="normalized_input_items_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_descriptor_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-descriptor",
            "client_turn_id": "turn-invalid-descriptor-1",
            "continuation_anchor_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": ["project.read_documents"],
            "resolved_tool_descriptor_snapshot": [
                {
                    "name": "project.read_documents",
                    "description": "读取文稿",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "origin": "project_document",
                    "trust_class": "local_first_party",
                    "plane": "resource",
                    "mutability": "read_only",
                    "execution_locus": "local_runtime",
                    "approval_mode": "unsafe_mode",
                    "idempotency_class": "safe_read",
                    "timeout_seconds": 15,
                }
            ],
            "turn_context_hash": "2" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="approval_mode"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_tool_policy_decision_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-policy-decision",
            "client_turn_id": "turn-invalid-policy-decision-1",
            "continuation_anchor_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [
                {
                    "descriptor": {
                        "name": "project.read_documents",
                        "description": "读取文稿",
                        "input_schema": {"type": "object"},
                        "output_schema": {"type": "object"},
                        "origin": "project_document",
                        "trust_class": "local_first_party",
                        "plane": "resource",
                        "mutability": "read_only",
                        "execution_locus": "local_runtime",
                        "approval_mode": "none",
                        "idempotency_class": "safe_read",
                        "timeout_seconds": 15,
                    },
                    "visibility": "visible",
                    "effective_approval_mode": "none",
                    "allowed_target_document_refs": [],
                    "hidden_reason": "write_grant_unavailable",
                }
            ],
            "turn_context_hash": "3" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="hidden_reason"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_budget_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-budget",
            "client_turn_id": "turn-invalid-budget-1",
            "continuation_anchor_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": {
                "max_steps": 0,
                "max_tool_calls": None,
                "max_input_tokens": None,
                "max_history_tokens": None,
                "max_tool_schema_tokens": None,
                "max_tool_result_tokens_per_step": None,
                "max_read_bytes": None,
                "max_write_bytes": None,
                "max_parallel_tool_calls": 1,
                "tool_timeout_seconds": None,
            },
            "turn_context_hash": "4" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="budget_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_compaction_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-compaction",
            "client_turn_id": "turn-invalid-compaction-1",
            "continuation_anchor_snapshot": None,
            "compaction_snapshot": {
                "trigger_reason": "max_input_tokens_exceeded",
                "phase": "initial_prompt",
                "level": "soft",
                "budget_limit_tokens": 216,
                "estimated_tokens_before": 240,
                "estimated_tokens_after": 120,
                "compressed_message_count": 2,
                "preserved_recent_message_count": 1,
                "protected_document_paths": ["数据层/人物关系.json"],
                "protected_document_refs": ["doc.characters"],
                "protected_document_reasons": {
                    "数据层/人物关系.json": ["selected_path", 1]
                },
                "protected_document_binding_versions": {"doc.characters": "binding-v1"},
                "document_context_recovery_snapshot": {
                    "active_path": "设定/人物.md",
                    "active_document_ref": "doc.characters",
                    "active_binding_version": "binding:v1",
                    "selected_paths": ["设定/人物.md"],
                    "selected_document_refs": ["doc.characters"],
                    "active_buffer_state": {"dirty": True, "unexpected": "invalid"},
                    "catalog_version": "catalog:v1",
                },
                "summary": "人物关系与势力关系要贯穿全文。",
            },
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": None,
            "turn_context_hash": "5" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="compaction_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_continuation_compaction_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-continuation-compaction",
            "client_turn_id": "turn-invalid-continuation-compaction-1",
            "continuation_anchor_snapshot": None,
            "compaction_snapshot": None,
            "continuation_compaction_snapshot": {
                "trigger_reason": "max_input_tokens_exceeded",
                "phase": "tool_loop_continuation",
                "level": "soft",
                "budget_limit_tokens": 280,
                "estimated_tokens_before": 410,
                "estimated_tokens_after": 0,
                "compacted_item_count": 2,
                "retained_item_count": 2,
                "compacted_tool_names": ["project.read_documents"],
                "trimmed_text_slot_count": 1,
                "dropped_content_item_count": 0,
            },
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": None,
            "turn_context_hash": "5" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="continuation_compaction_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_continuation_request_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-continuation-request",
            "client_turn_id": "turn-invalid-continuation-request-1",
            "continuation_anchor_snapshot": None,
            "compaction_snapshot": None,
            "continuation_request_snapshot": {
                "continuation_items": ["invalid"],
                "provider_continuation_state": None,
            },
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": None,
            "turn_context_hash": "6" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="continuation_request_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_document_context_recovery_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-document-context-recovery",
            "client_turn_id": "turn-invalid-document-context-recovery-1",
            "continuation_anchor_snapshot": None,
            "compaction_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "document_context_recovery_snapshot": {
                "active_path": "设定/人物.md",
                "active_document_ref": "doc.characters",
                "active_binding_version": "binding:v1",
                "selected_paths": ["设定/人物.md"],
                "selected_document_refs": ["doc.characters"],
                "active_buffer_state": {"dirty": True, "unexpected": "invalid"},
                "catalog_version": None,
            },
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": None,
            "turn_context_hash": "6" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="document_context_recovery_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_document_context_injection_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-document-context-injection",
            "client_turn_id": "turn-invalid-document-context-injection-1",
            "continuation_anchor_snapshot": None,
            "compaction_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "document_context_recovery_snapshot": None,
            "document_context_injection_snapshot": {
                "active_path": "设定/人物.md",
                "selected_paths": ["设定/人物.md"],
                "selected_document_refs": ["doc.characters"],
                "active_buffer_state": {"dirty": True, "unexpected": "invalid"},
            },
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": None,
            "turn_context_hash": "6" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="document_context_injection_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_tool_guidance_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-tool-guidance",
            "client_turn_id": "turn-invalid-tool-guidance-1",
            "continuation_anchor_snapshot": None,
            "compaction_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "document_context_recovery_snapshot": None,
            "tool_guidance_snapshot": {
                "guidance_type": "project_search_then_read",
                "tool_names": ["project.search_documents", "project.read_documents"],
                "trigger_keywords": "人物关系",
                "content": "【项目范围工具提示】\n- 当前对话已绑定项目。",
            },
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": None,
            "turn_context_hash": "6" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="tool_guidance_snapshot"):
        store.get_run(run_id)


def test_assistant_turn_run_store_rejects_invalid_continuation_anchor_snapshot(tmp_path) -> None:
    store = AssistantTurnRunStore(tmp_path / "turn-runs")
    run_id = uuid.uuid4()
    snapshot_path = store.root / f"{run_id}.json"
    _write_turn_run_snapshot(
        snapshot_path,
        {
            "run_id": str(run_id),
            "owner_id": str(uuid.uuid4()),
            "project_id": None,
            "conversation_id": "conversation-invalid-continuation-anchor",
            "client_turn_id": "turn-invalid-continuation-anchor-1",
            "continuation_anchor_snapshot": {
                "previous_run_id": "not-a-uuid",
                "messages_digest": 123,
            },
            "compaction_snapshot": None,
            "request_messages_digest": "digest",
            "document_context_snapshot": None,
            "requested_write_scope": "disabled",
            "requested_write_targets_snapshot": [],
            "normalized_input_items_snapshot": [{"item_type": "message", "role": "user", "content": "hi"}],
            "exposed_tool_names_snapshot": [],
            "resolved_tool_descriptor_snapshot": [],
            "tool_policy_decisions_snapshot": [],
            "budget_snapshot": None,
            "turn_context_hash": "7" * 64,
            "terminal_status": "completed",
            "completion_messages_digest": "digest+assistant",
            "terminal_error_code": None,
            "terminal_error_message": None,
            "write_effective": False,
            "completed_at": "2026-04-05T00:00:00+00:00",
        },
    )

    with pytest.raises(ConfigurationError, match="continuation_anchor_snapshot"):
        store.get_run(run_id)


async def test_assistant_service_surfaces_partial_project_read_errors_to_followup_prompt(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ToolLoopErrorEchoProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
        ),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊")
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="找一下人物和缺失文稿，再告诉我情况。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert response.content.startswith("我看到人物文稿已读到")
    assert _request_contains_continuation_fragment(tool_provider.requests[1], "设定/不存在.md")
    assert _request_contains_continuation_fragment(tool_provider.requests[1], "document_not_found")


async def test_assistant_service_fails_when_tool_loop_exhausted(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _InfiniteToolCallProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            max_iterations=2,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊")
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="一直循环读人物设定。")],
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        await service.turn(async_db(db), payload, owner_id=owner.id)

    failed_run = turn_run_store.get_run(
        build_turn_run_id(
            owner_id=owner.id,
            project_id=project.id,
            conversation_id=payload.conversation_id,
            client_turn_id=payload.client_turn_id,
        )
    )

    assert exc_info.value.code == "tool_loop_exhausted"
    assert str(exc_info.value) == "本轮工具调用次数已达上限，已停止继续执行。"
    assert failed_run is not None
    assert failed_run.exposed_tool_names_snapshot == (
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
    )
    assert failed_run.resolved_tool_descriptor_snapshot[0]["approval_mode"] == "none"
    assert failed_run.requested_write_scope == "disabled"
    assert failed_run.budget_snapshot == _expected_run_budget(max_steps=2, tool_timeout_seconds=15)
    assert failed_run.turn_context_hash
    assert failed_run.terminal_status == "failed"
    assert failed_run.terminal_error_code == "tool_loop_exhausted"
    assert failed_run.write_effective is False


async def test_assistant_service_executes_multiple_tool_calls_from_single_model_turn(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ParallelToolCallProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            max_iterations=4,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊")
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="并行读一下人物设定。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    completed_run = turn_run_store.get_run(
        build_turn_run_id(
            owner_id=owner.id,
            project_id=project.id,
            conversation_id=payload.conversation_id,
            client_turn_id=payload.client_turn_id,
        )
    )

    assert response.content == "我已按顺序读取人物设定，可以继续给出分析。"
    assert [item.item_type for item in response.output_items] == [
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_result",
        "text",
    ]
    assert response.output_items[0].call_id == "call.project.read_documents.1"
    assert response.output_items[2].call_id == "call.project.read_documents.2"
    assert completed_run is not None
    assert completed_run.budget_snapshot == _expected_run_budget(max_steps=4, tool_timeout_seconds=15)
    assert completed_run.budget_snapshot["max_parallel_tool_calls"] == 1
    assert completed_run.terminal_status == "completed"
    assert completed_run.terminal_error_code is None


async def test_assistant_service_preserves_terminal_payload_when_on_error_hook_also_fails(
    db,
    tmp_path,
    monkeypatch,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊：冷静、克制。")
    target = next(
        item
        for item in await capability_service.list_document_catalog(async_db(db), project.id)
        if item.path == "设定/人物.md"
    )
    tool_provider = _WriteDocumentToolProvider(base_version=target.version)
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=_FailOnCommittedStepStore(tmp_path / "tool-steps"),
        ),
        turn_run_store=turn_run_store,
    )

    original_run_hook_event = service._run_hook_event

    async def _patched_run_hook_event(db, hooks, event, **kwargs):
        if event == "on_error":
            raise RuntimeError("on_error hook failed")
        return await original_run_hook_event(db, hooks, event, **kwargs)

    monkeypatch.setattr(service, "_run_hook_event", _patched_run_hook_event)

    current_content = "# 人物\n\n林渊：冷静、克制。"
    payload = _build_turn_request(
        project_id=project.id,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="把当前人物设定补一条观察能力。")],
    )

    with pytest.raises(ExceptionGroup):
        await service.turn(async_db(db), payload, owner_id=owner.id)

    failed_run = turn_run_store.get_run(
        build_turn_run_id(
            owner_id=owner.id,
            project_id=project.id,
            conversation_id=payload.conversation_id,
            client_turn_id=payload.client_turn_id,
        )
    )

    assert failed_run is not None
    assert failed_run.terminal_status == "failed"
    assert failed_run.terminal_error_code == "committed_state_persist_failed"
    assert failed_run.write_effective is True
    assert failed_run.terminal_error_message is not None
    assert "文稿写入已生效" in failed_run.terminal_error_message


async def test_assistant_service_runs_project_write_document_tool_loop(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    current_content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    target = next(
        item
        for item in await capability_service.list_document_catalog(async_db(db), project.id)
        if item.path == "设定/人物.md"
    )
    tool_provider = _WriteDocumentToolProvider(base_version=target.version)
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    payload = _build_turn_request(
        project_id=project.id,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="把当前人物设定补一条观察能力。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)
    saved = file_store.find_project_document(project.id, "设定/人物.md")

    assert response.content.startswith("人物设定已经同步")
    assert [item.item_type for item in response.output_items] == ["tool_call", "tool_result", "text"]
    assert response.output_items[1].payload["structured_output"]["path"] == "设定/人物.md"
    assert saved is not None
    assert "他对雨夜里的细微异常尤其敏感" in saved.content
    step_history = step_store.list_step_history(response.run_id, "call.project.write_document.1")
    run_record = turn_run_store.get_run(response.run_id)
    assert run_record is not None
    assert [item.status for item in step_history] == ["validating", "writing", "committed"]
    assert step_history[-1].idempotency_key == f"{response.run_id}:call.project.write_document.1:{target.document_ref}"
    assert step_history[-1].approval_grant_id is not None
    assert step_history[-1].approval_grant_snapshot == {
        "grant_id": step_history[-1].approval_grant_id,
        "allowed_tool_names": ["project.write_document"],
        "target_document_refs": [target.document_ref],
        "binding_version_constraints": {
            target.document_ref: run_record.document_context_bindings_snapshot[0]["binding_version"]
        },
        "base_version_constraints": {
            target.document_ref: target.version
        },
        "approval_mode_snapshot": "grant_bound",
        "buffer_hash_constraints": {
            target.document_ref: build_project_document_buffer_hash(current_content)
        },
        "buffer_source_constraints": {
            target.document_ref: TRUSTED_ACTIVE_BUFFER_SOURCE
        },
        "expires_at": None,
    }
    assert step_history[-1].result_summary == {
        "resource_count": 1,
        "content_item_count": 1,
        "paths": ["设定/人物.md"],
        "document_count": 1,
        "document_revision_id": response.output_items[1].payload["structured_output"]["document_revision_id"],
        "run_audit_id": response.output_items[1].payload["structured_output"]["run_audit_id"],
    }
    assert run_record.requested_write_scope == "turn"
    assert run_record.requested_write_targets_snapshot == (target.document_ref,)
    assert len(run_record.approval_grants_snapshot) == 1
    assert run_record.approval_grants_snapshot[0] == {
        "grant_id": step_history[-1].approval_grant_id,
        "allowed_tool_names": ("project.write_document",),
        "target_document_refs": (target.document_ref,),
        "binding_version_constraints": {
            target.document_ref: run_record.document_context_bindings_snapshot[0]["binding_version"]
        },
        "base_version_constraints": {
            target.document_ref: target.version
        },
        "approval_mode_snapshot": "grant_bound",
        "buffer_hash_constraints": {
            target.document_ref: build_project_document_buffer_hash(current_content)
        },
        "buffer_source_constraints": {
            target.document_ref: TRUSTED_ACTIVE_BUFFER_SOURCE
        },
        "expires_at": None,
    }
    assert run_record.document_context_snapshot is not None
    assert run_record.document_context_recovery_snapshot is not None
    assert run_record.document_context_injection_snapshot is not None
    assert run_record.tool_catalog_version is not None
    assert run_record.tool_catalog_version.startswith("tool_catalog:")
    assert run_record.tool_catalog_version != run_record.document_context_snapshot["catalog_version"]
    assert run_record.document_context_snapshot["active_path"] == "设定/人物.md"
    assert run_record.document_context_recovery_snapshot["active_path"] == "设定/人物.md"
    assert run_record.document_context_recovery_snapshot["active_document_ref"] == target.document_ref
    assert (
        run_record.document_context_recovery_snapshot["active_binding_version"]
        == run_record.document_context_bindings_snapshot[0]["binding_version"]
    )
    assert run_record.document_context_recovery_snapshot["selected_paths"] == ["设定/人物.md"]
    assert run_record.document_context_recovery_snapshot["selected_document_refs"] == [target.document_ref]
    assert (
        run_record.document_context_recovery_snapshot["active_buffer_state"]["source"]
        == TRUSTED_ACTIVE_BUFFER_SOURCE
    )
    document_context_recovery_item = next(
        item
        for item in run_record.normalized_input_items_snapshot
        if item["item_type"] == "document_context_recovery"
    )
    assert document_context_recovery_item["payload"] == run_record.document_context_recovery_snapshot
    assert run_record.document_context_injection_snapshot == (
        build_document_context_injection_snapshot(
            run_record.document_context_snapshot,
            document_context_recovery_snapshot=run_record.document_context_recovery_snapshot,
        )
    )
    assert run_record.document_context_bindings_snapshot[0]["document_ref"] == target.document_ref
    assert run_record.document_context_bindings_snapshot[0]["selection_role"] == "active"
    assert run_record.document_context_bindings_snapshot[0]["buffer_source"] == TRUSTED_ACTIVE_BUFFER_SOURCE
    assert set(run_record.exposed_tool_names_snapshot) == {
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
        "project.write_document",
    }
    assert run_record.budget_snapshot == _expected_run_budget(max_steps=8, tool_timeout_seconds=None)
    assert run_record.status == "completed"
    assert run_record.write_effective is True
    assert {item["name"] for item in run_record.resolved_tool_descriptor_snapshot} == {
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
        "project.write_document",
    }
    policy_by_name = {
        item["descriptor"]["name"]: item
        for item in run_record.tool_policy_decisions_snapshot
    }
    assert policy_by_name["project.list_documents"]["visibility"] == "visible"
    assert policy_by_name["project.search_documents"]["visibility"] == "visible"
    assert policy_by_name["project.read_documents"]["visibility"] == "visible"
    assert policy_by_name["project.write_document"]["visibility"] == "visible"
    assert policy_by_name["project.write_document"]["allowed_target_document_refs"] == (target.document_ref,)
    assert policy_by_name["project.write_document"]["approval_grant"] == run_record.approval_grants_snapshot[0]
    assert (
        response.output_items[1].payload["structured_output"]["run_audit_id"]
        == f"{response.run_id}:call.project.write_document.1"
    )
    assert response.output_items[1].payload["audit"] == {
        "run_audit_id": f"{response.run_id}:call.project.write_document.1"
    }
    tool_result_item = next(
        item
        for item in run_record.normalized_input_items_snapshot
        if item["item_type"] == "tool_result"
    )
    assert tool_result_item["payload"]["audit"] == response.output_items[1].payload["audit"]
    assert tool_result_item["payload"]["structured_output"]["path"] == "设定/人物.md"
    assert any(
        item["item_type"] == "tool_call"
        for item in run_record.normalized_input_items_snapshot
    )


async def test_assistant_service_surfaces_write_document_conflict_to_followup_prompt(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _WriteConflictToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    current_content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    payload = _build_turn_request(
        project_id=project.id,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version="sha256:stale",
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="尝试覆盖旧版本人物设定。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert response.content.startswith("写回失败，因为人物设定已经有新版本")
    assert len(tool_provider.requests) == 2
    assert _request_contains_continuation_fragment(tool_provider.requests[1], "version_conflict")
    run_id = build_turn_run_id(
        owner_id=owner.id,
        project_id=project.id,
        conversation_id=payload.conversation_id,
        client_turn_id=payload.client_turn_id,
    )
    step_history = step_store.list_step_history(
        run_id,
        "call.project.write_document.conflict",
    )
    assert [item.status for item in step_history] == ["validating", "failed"]
    assert step_history[-1].tool_name == "project.write_document"
    assert step_history[-1].error_code == "version_conflict"
    assert step_history[-1].result_summary == {
        "content_item_count": 0,
        "error_code": "version_conflict",
        "message": "目标文稿版本已变化，请重新读取最新内容后再写入。",
        "recovery_kind": "return_error_to_model",
        "resource_count": 0,
    }
    assert response.output_items[1].payload["error"] == {
        "code": "version_conflict",
        "message": "目标文稿版本已变化，请重新读取最新内容后再写入。",
        "retryable": False,
        "recovery_hint": "请先重新读取目标文稿的最新状态，再决定是否继续写入。",
        "requires_user_action": True,
        "recovery_kind": "return_error_to_model",
    }


async def test_assistant_service_stream_turn_surfaces_write_document_conflict_and_continues(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _WriteConflictToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    current_content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version="sha256:stale",
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="尝试覆盖旧版本人物设定。")],
    )

    events = [event async for event in service.stream_turn(async_db(db), payload, owner_id=owner.id)]

    assert [event.event for event in events] == [
        "run_started",
        "tool_call_start",
        "tool_call_result",
        "chunk",
        "chunk",
        "completed",
    ]
    assert [event.data["state_version"] for event in events] == [1, 2, 2, 4, 4, 6]
    assert events[1].data["target_summary"] == {
        "path": "设定/人物.md",
        "base_version": "sha256:stale",
    }
    assert "arguments" not in events[1].data
    assert "arguments_text" not in events[1].data
    assert events[2].data["status"] == "errored"
    assert events[2].data["result_summary"] == {
        "content_item_count": 0,
        "error_code": "version_conflict",
        "message": "目标文稿版本已变化，请重新读取最新内容后再写入。",
        "recovery_kind": "return_error_to_model",
        "resource_count": 0,
    }
    assert events[2].data["error"] == {
        "code": "version_conflict",
        "message": "目标文稿版本已变化，请重新读取最新内容后再写入。",
        "retryable": False,
        "recovery_hint": "请先重新读取目标文稿的最新状态，再决定是否继续写入。",
        "requires_user_action": True,
        "recovery_kind": "return_error_to_model",
    }
    assert events[-1].data["content"].startswith("写回失败，因为人物设定已经有新版本")


async def test_assistant_service_stream_turn_surfaces_committed_write_when_step_persist_fails(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    current_content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    target = next(
        item
        for item in await capability_service.list_document_catalog(async_db(db), project.id)
        if item.path == "设定/人物.md"
    )
    tool_provider = _WriteDocumentToolProvider(base_version=target.version)
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = _FailOnCommittedStepStore(tmp_path / "tool-steps")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
    )
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="把当前人物设定补一条观察能力。")],
    )

    events: list[AssistantStreamEvent] = []
    with pytest.raises(BusinessRuleError) as exc_info:
        async for event in service.stream_turn(async_db(db), payload, owner_id=owner.id):
            events.append(event)

    saved = file_store.find_project_document(project.id, "设定/人物.md")
    failed_run_id = build_turn_run_id(
        owner_id=owner.id,
        project_id=project.id,
        conversation_id=payload.conversation_id,
        client_turn_id=payload.client_turn_id,
    )
    step_history = step_store.list_step_history(
        failed_run_id,
        "call.project.write_document.1",
    )

    assert exc_info.value.code == "committed_state_persist_failed"
    assert "文稿写入已生效" in str(exc_info.value)
    assert saved is not None
    assert "他对雨夜里的细微异常尤其敏感" in saved.content
    assert [item.status for item in step_history] == ["validating", "writing"]
    assert [event.event for event in events] == [
        "run_started",
        "tool_call_start",
        "tool_call_result",
    ]
    assert events[-1].data["status"] == "committed"
    assert events[-1].data["result_summary"]["state_persist_failed"] is True
    assert events[-1].data["result_summary"]["document_revision_id"]
    assert events[-1].data["error"]["code"] == "committed_state_persist_failed"


async def test_assistant_service_stream_turn_surfaces_effective_write_when_revision_persist_fails(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
        document_revision_store=_FailOnAppendRevisionStore(tmp_path / "revisions"),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    current_content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    target = next(
        item
        for item in await capability_service.list_document_catalog(async_db(db), project.id)
        if item.path == "设定/人物.md"
    )
    tool_provider = _WriteDocumentToolProvider(base_version=target.version)
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="把当前人物设定补一条观察能力。")],
    )

    events: list[AssistantStreamEvent] = []
    with pytest.raises(BusinessRuleError) as exc_info:
        async for event in service.stream_turn(async_db(db), payload, owner_id=owner.id):
            events.append(event)

    saved = file_store.find_project_document(project.id, "设定/人物.md")
    run_id = build_turn_run_id(
        owner_id=owner.id,
        project_id=project.id,
        conversation_id=payload.conversation_id,
        client_turn_id=payload.client_turn_id,
    )
    run_record = turn_run_store.get_run(run_id)
    step_history = step_store.list_step_history(run_id, "call.project.write_document.1")

    assert exc_info.value.code == "document_revision_persist_failed"
    assert saved is not None
    assert "他对雨夜里的细微异常尤其敏感" in saved.content
    assert [item.status for item in step_history] == ["validating", "writing", "committed"]
    assert events[-1].data["status"] == "committed"
    assert events[-1].data["result_summary"]["write_effective"] is True
    assert events[-1].data["error"]["code"] == "document_revision_persist_failed"
    assert run_record is not None
    assert run_record.write_effective is True
    assert run_record.terminal_error_code == "document_revision_persist_failed"


async def test_assistant_service_stream_turn_preserves_effective_write_when_cancelled_after_commit(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    current_content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    target = next(
        item
        for item in await capability_service.list_document_catalog(async_db(db), project.id)
        if item.path == "设定/人物.md"
    )
    tool_provider = _WriteDocumentToolProvider(base_version=target.version)
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        requested_write_scope="turn",
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
        },
        messages=[AssistantMessageDTO(role="user", content="把当前人物设定补一条观察能力。")],
    )
    should_stop_calls = 0

    async def should_stop() -> bool:
        nonlocal should_stop_calls
        should_stop_calls += 1
        return should_stop_calls >= 4

    events: list[AssistantStreamEvent] = []
    with pytest.raises(BusinessRuleError) as exc_info:
        async for event in service.stream_turn(
            async_db(db),
            payload,
            owner_id=owner.id,
            should_stop=should_stop,
        ):
            events.append(event)

    saved = file_store.find_project_document(project.id, "设定/人物.md")
    run_id = build_turn_run_id(
        owner_id=owner.id,
        project_id=project.id,
        conversation_id=payload.conversation_id,
        client_turn_id=payload.client_turn_id,
    )
    run_record = turn_run_store.get_run(run_id)
    step_history = step_store.list_step_history(run_id, "call.project.write_document.1")

    assert exc_info.value.code == "cancel_requested"
    assert str(exc_info.value) == "本轮已停止，但已有写入生效。"
    assert saved is not None
    assert "他对雨夜里的细微异常尤其敏感" in saved.content
    assert [event.event for event in events] == [
        "run_started",
        "tool_call_start",
        "tool_call_result",
    ]
    assert events[-1].data["status"] == "committed"
    assert [item.status for item in step_history] == ["validating", "writing", "committed"]
    assert run_record is not None
    assert run_record.terminal_status == "cancelled"
    assert run_record.write_effective is True
    assert run_record.terminal_error_code == "cancel_requested"
    assert run_record.terminal_error_message == "本轮已停止，但已有写入生效。"


async def test_assistant_service_stream_turn_records_cancelled_tool_step_before_execution(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ToolCallingFakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
        turn_run_store=turn_run_store,
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(
        project.id,
        "设定/人物.md",
        "# 人物\n\n林渊：冷静、克制，擅长从细枝末节里发现异常。",
    )
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="先读一下人物设定，再给我一个悬疑开场方向。")],
    )
    should_stop_calls = 0

    async def should_stop() -> bool:
        nonlocal should_stop_calls
        should_stop_calls += 1
        return should_stop_calls >= 3

    events: list[AssistantStreamEvent] = []
    with pytest.raises(StreamInterruptedError):
        async for event in service.stream_turn(
            async_db(db),
            payload,
            owner_id=owner.id,
            should_stop=should_stop,
        ):
            events.append(event)

    cancelled_run_id = build_turn_run_id(
        owner_id=owner.id,
        project_id=project.id,
        conversation_id=payload.conversation_id,
        client_turn_id=payload.client_turn_id,
    )
    run_record = turn_run_store.get_run(cancelled_run_id)
    step_history = step_store.list_step_history(cancelled_run_id, "call.project.read_documents.1")

    assert [event.event for event in events] == [
        "run_started",
        "tool_call_start",
        "tool_call_result",
    ]
    assert events[-1].data["status"] == "cancelled"
    assert events[-1].data["result_summary"] == {
        "cancelled": True,
        "terminal": True,
        "error_code": "cancel_requested",
        "message": "本轮已停止，当前工具未执行。",
    }
    assert [item.status for item in step_history] == ["reading", "cancelled"]
    assert step_history[-1].error_code == "cancel_requested"
    assert run_record is not None
    assert run_record.terminal_status == "cancelled"
    assert run_record.terminal_error_code == "cancel_requested"


async def test_assistant_service_rejects_stale_document_context_catalog_version(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        project_document_capability_service=capability_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊：冷静、克制。")
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "catalog_version": "catalog:stale",
        },
        messages=[AssistantMessageDTO(role="user", content="继续参考当前人物设定。")],
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        await service.turn(async_db(db), payload, owner_id=owner.id)

    assert exc_info.value.code == "catalog_version_mismatch"
    assert str(exc_info.value) == "当前文稿目录已变化，请刷新文稿上下文后重试。"
    assert tool_provider.requests == []


async def test_assistant_service_accepts_stale_catalog_version_when_active_binding_is_stable(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        project_document_capability_service=capability_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊：冷静、克制。")
    catalog = await capability_service.list_document_catalog(async_db(db), project.id, owner_id=owner.id)
    target = next(item for item in catalog if item.path == "设定/人物.md")
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_document_ref": target.document_ref,
            "active_binding_version": target.binding_version,
            "catalog_version": "catalog:stale",
        },
        messages=[AssistantMessageDTO(role="user", content="继续参考当前人物设定。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert response.content.startswith("主回复：")
    assert len(tool_provider.requests) == 1


async def test_assistant_service_rejects_active_document_binding_drift(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        project_document_capability_service=capability_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    content = "# 人物\n\n林渊：冷静、克制。"
    file_store.save_project_document(project.id, "设定/人物.md", content)
    stale_entry = next(
        item
        for item in await capability_service.list_document_catalog(async_db(db), project.id)
        if item.path == "设定/人物.md"
    )
    file_store.delete_project_document_entry(project.id, "设定/人物.md")
    identity_store.delete_document_ref(project.id, path="设定/人物.md")
    file_store.save_project_document(project.id, "设定/人物.md", content)
    fresh_entry = next(
        item
        for item in await capability_service.list_document_catalog(async_db(db), project.id)
        if item.path == "设定/人物.md"
    )

    assert stale_entry.document_ref != fresh_entry.document_ref
    assert stale_entry.version == fresh_entry.version

    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        document_context={
            "active_path": "设定/人物.md",
            "active_document_ref": stale_entry.document_ref,
            "active_binding_version": stale_entry.binding_version,
            "active_buffer_state": _build_trusted_active_buffer_state(
                base_version=stale_entry.version,
                content="# 人物\n\n林渊",
            ),
            "catalog_version": fresh_entry.catalog_version,
        },
        messages=[AssistantMessageDTO(role="user", content="继续参考当前人物设定。")],
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        await service.turn(async_db(db), payload, owner_id=owner.id)

    assert exc_info.value.code == "active_document_binding_mismatch"
    assert str(exc_info.value) == "当前活动文稿绑定已变化，请刷新当前文稿后重试。"
    assert tool_provider.requests == []


async def test_assistant_service_stream_turn_emits_tool_events_for_project_read_documents(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ToolCallingFakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
        ),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(
        project.id,
        "设定/人物.md",
        "# 人物\n\n林渊：冷静、克制，擅长从细枝末节里发现异常。",
    )
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="先读一下人物设定，再给我一个悬疑开场方向。")],
    )

    events = [event async for event in service.stream_turn(async_db(db), payload, owner_id=owner.id)]

    assert [event.event for event in events] == [
        "run_started",
        "tool_call_start",
        "tool_call_result",
        "chunk",
        "chunk",
        "completed",
    ]
    assert [event.data["event_seq"] for event in events] == [1, 2, 3, 4, 5, 6]
    assert [event.data["state_version"] for event in events] == [1, 2, 3, 4, 5, 6]
    assert events[1].data["tool_call_id"] == "call.project.read_documents.1"
    assert events[1].data["tool_name"] == "project.read_documents"
    assert events[1].data["target_summary"]["paths"] == ["设定/人物.md"]
    assert events[2].data["status"] == "completed"
    assert events[2].data["result_summary"]["paths"] == ["设定/人物.md"]
    assert all("chunk_kind" not in event.data for event in events[3:5])
    assert "".join(event.data["delta"] for event in events[3:5]).startswith("我已经读完人物设定")
    assert events[-1].data["content"].startswith("我已经读完人物设定")


async def test_assistant_service_stream_turn_keeps_true_provider_stream_for_project_turn_without_tool_call(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _ProjectStreamingFakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
        ),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="给我一个冷峻克制的开场方向。")],
    )

    events = [event async for event in service.stream_turn(async_db(db), payload, owner_id=owner.id)]

    assert [event.event for event in events] == ["run_started", "chunk", "chunk", "chunk", "completed"]
    assert [event.data["event_seq"] for event in events] == [1, 2, 3, 4, 5]
    assert [event.data["state_version"] for event in events] == [1, 2, 3, 4, 5]
    assert [event.data["delta"] for event in events[1:4]] == ["第一句。", "第二句。", "第三句。"]
    assert all("chunk_kind" not in event.data for event in events[1:4])
    assert events[-1].data["content"] == "第一句。第二句。第三句。"


async def test_assistant_service_stream_turn_runs_on_error_hook_for_project_tool_stream(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    _write_yaml(
        config_root / "hooks" / "on-error-summary.yaml",
        """
hook:
  id: "hook.on_error_summary"
  name: "流式失败摘要"
  trigger:
    event: "on_error"
  action:
    type: "agent"
    config:
      agent_id: "agent.hook_summary"
      input_mapping:
        content: "error.message"
""",
    )
    loader = ConfigLoader(config_root)
    tool_provider = _FailingProjectStreamToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
        ),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    payload = _build_turn_request(
        project_id=project.id,
        stream=True,
        hook_ids=["hook.on_error_summary"],
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="故意触发流式失败")],
    )

    events: list = []
    with pytest.raises(ConfigurationError, match="上游流式失败"):
        async for event in service.stream_turn(async_db(db), payload, owner_id=owner.id):
            events.append(event)

    assert [event.event for event in events] == ["run_started"]
    summary_prompts = [
        prompt
        for prompt in tool_provider.prompts
        if "请根据以下内容输出一句摘要" in prompt
    ]
    assert len(summary_prompts) == 1


async def test_assistant_service_turn_runs_on_error_hook_for_prepare_failure(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    _write_yaml(
        config_root / "hooks" / "on-error-summary.yaml",
        """
hook:
  id: "hook.on_error_summary"
  name: "失败摘要"
  trigger:
    event: "on_error"
  action:
    type: "agent"
    config:
      agent_id: "agent.hook_summary"
      input_mapping:
        content: "error.message"
""",
    )
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
        turn_run_store=turn_run_store,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-prepare-on-error")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                hook_ids=["hook.on_error_summary"],
                continuation_anchor=AssistantContinuationAnchorDTO(previous_run_id=uuid.uuid4()),
                messages=[AssistantMessageDTO(role="user", content="继续往下展开。")],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )

            with pytest.raises(BusinessRuleError, match="当前会话状态已变化"):
                await service.turn(session, payload, owner_id=owner_id)

        summary_prompts = [
            prompt
            for prompt in tool_provider.prompts
            if "请根据以下内容输出一句摘要" in prompt
        ]
        assert len(summary_prompts) == 1
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_stream_turn_runs_on_error_hook_for_finalize_failure(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    _write_yaml(
        config_root / "hooks" / "on-error-summary.yaml",
        """
hook:
  id: "hook.on_error_summary"
  name: "失败摘要"
  trigger:
    event: "on_error"
  action:
    type: "agent"
    config:
      agent_id: "agent.hook_summary"
      input_mapping:
        content: "error.message"
""",
    )
    loader = ConfigLoader(config_root)
    tool_provider = _EmptyContentToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-finalize-on-error")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                stream=True,
                hook_ids=["hook.on_error_summary"],
                messages=[AssistantMessageDTO(role="user", content="给我一个方向。")],
                model={"provider": "openai", "name": "gpt-4o-mini"},
            )

            events: list[AssistantStreamEvent] = []
            with pytest.raises(ConfigurationError, match="Assistant output must be plain text"):
                async for event in service.stream_turn(session, payload, owner_id=owner_id):
                    events.append(event)

        assert [event.event for event in events] == ["run_started"]
        summary_prompts = [
            prompt
            for prompt in tool_provider.prompts
            if "请根据以下内容输出一句摘要" in prompt
        ]
        assert len(summary_prompts) == 1
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_uses_project_mcp_for_project_hook(tmp_path) -> None:
    class _ProjectAwareMcpToolCaller:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str, dict]] = []

        async def call_tool(self, *, server, tool_name: str, arguments: dict) -> McpToolCallResult:
            self.calls.append((server.id, server.url, tool_name, arguments))
            return McpToolCallResult(
                content=[{"type": "text", "text": "来自项目 MCP 的查询结果"}],
                structured_content={"headline": "项目热点"},
                is_error=False,
            )

    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    mcp_tool_caller = _ProjectAwareMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    mcp_service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    service = AssistantService(
        assistant_mcp_service=mcp_service,
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        mcp_server_resolver=lambda context, server_id: mcp_service.resolve_mcp_server(
            server_id,
            owner_id=context.owner_id,
            project_id=context.project_id,
        ),
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-mcp-runtime")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        project_mcp_file = (
            tmp_path
            / "assistant-config"
            / "projects"
            / str(project.id)
            / "mcp_servers"
            / "mcp.news.lookup"
            / "MCP.yaml"
        )
        project_mcp_file.parent.mkdir(parents=True, exist_ok=True)
        project_mcp_file.write_text(
            "\n".join(
                [
                    "mcp_server:",
                    "  id: mcp.news.lookup",
                    "  name: 项目新闻查询",
                    "  enabled: true",
                    "  version: \"1.0.0\"",
                    "  transport: streamable_http",
                    "  url: https://example.com/project-mcp",
                    "  headers: {}",
                    "  timeout: 30",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        async with async_session_factory() as session:
            payload = _build_turn_request(
                agent_id="agent.general_assistant",
                project_id=project.id,
                hook_ids=["hook.before_news_lookup"],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        assert mcp_tool_caller.calls == [
            (
                "mcp.news.lookup",
                "https://example.com/project-mcp",
                "search_news",
                {"query": "今天有什么新闻？"},
            )
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_stream_turn_yields_chunks_and_completed_event(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-stream-service")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                stream=True,
                messages=[AssistantMessageDTO(role="user", content="给我一个故事方向。")],
            )
            events = [
                event async for event in service.stream_turn(session, payload, owner_id=owner_id)
            ]

        assert [event.event for event in events] == ["run_started", "chunk", "chunk", "completed"]
        assert events[0].data["run_id"]
        assert events[0].data["conversation_id"] == "conversation-test"
        assert "".join(event.data["delta"] for event in events[1:-1]) == (
            "主回复：今天的重点新闻主要集中在科技和国际动态。"
        )
        assert events[-1].data["content"].startswith("主回复：")
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_agent_hook_after_response(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-agent-hook")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                hook_ids=["hook.after_summary_agent"],
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[AssistantMessageDTO(role="user", content="帮我看看今天的新闻。")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.content.startswith("主回复：")
        assert response.hook_results[0].action_type == "agent"
        assert response.hook_results[0].result == "Hook 摘要完成。"
        assert any("请根据以下内容输出一句摘要" in prompt for prompt in tool_provider.prompts)
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_applies_preferences_and_rules_to_agent_hook(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(
            project_service=create_project_service(),
            config_store=assistant_store,
            credential_service_factory=_FakeCredentialService,
        ),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-agent-hook-preferences")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            await service.assistant_preferences_service.update_preferences(
                session,
                owner.id,
                AssistantPreferencesUpdateDTO(
                    default_provider="anthropic",
                    default_model_name="claude-sonnet-4",
                    default_max_output_tokens=8192,
                ),
            )
            await service.assistant_preferences_service.update_project_preferences(
                session,
                project.id,
                owner_id=owner.id,
                payload=AssistantPreferencesUpdateDTO(
                    default_provider="openai",
                    default_model_name="gpt-4.1",
                    default_max_output_tokens=3072,
                ),
            )
            await service.assistant_rule_service.update_user_rules(
                session,
                payload=AssistantRuleProfileUpdateDTO(enabled=True, content="先给结论。"),
                owner_id=owner.id,
            )
            await service.assistant_rule_service.update_project_rules(
                session,
                project.id,
                payload=AssistantRuleProfileUpdateDTO(
                    enabled=True,
                    content="这个项目统一写得更温柔一点。",
                ),
                owner_id=owner.id,
            )
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                project_id=project.id,
                hook_ids=["hook.after_summary_agent"],
                messages=[AssistantMessageDTO(role="user", content="帮我看看今天的新闻。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        hook_request = tool_provider.requests[-1]
        model = hook_request["model"]
        system_prompt = hook_request["system_prompt"] or ""
        assert isinstance(model, dict)
        assert model["provider"] == "openai"
        assert model["name"] == "gpt-4.1"
        assert model["max_tokens"] == 3072
        assert "【用户长期规则】" in system_prompt
        assert "先给结论。" in system_prompt
        assert "【当前项目规则】" in system_prompt
        assert "这个项目统一写得更温柔一点。" in system_prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_injects_user_and_project_rules(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-rules")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            await service.assistant_rule_service.update_user_rules(
                session,
                payload=AssistantRuleProfileUpdateDTO(enabled=True, content="回答时先给结论。"),
                owner_id=owner.id,
            )
            await service.assistant_rule_service.update_project_rules(
                session,
                project.id,
                payload=AssistantRuleProfileUpdateDTO(
                    enabled=True,
                    content="这个项目固定写成轻松治愈风。",
                ),
                owner_id=owner.id,
            )
            payload = _build_turn_request(
                agent_id="agent.general_assistant",
                project_id=project.id,
                messages=[AssistantMessageDTO(role="user", content="给我一个开头方向。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        system_prompt = tool_provider.requests[0]["system_prompt"] or ""
        assert "【用户长期规则】" in system_prompt
        assert "回答时先给结论。" in system_prompt
        assert "【当前项目规则】" in system_prompt
        assert "这个项目固定写成轻松治愈风。" in system_prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_without_skill_using_rules_and_current_conversation(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-no-skill")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            await service.assistant_rule_service.update_user_rules(
                session,
                payload=AssistantRuleProfileUpdateDTO(enabled=True, content="回答时先给一句方向判断。"),
                owner_id=owner.id,
            )
            await service.assistant_rule_service.update_project_rules(
                session,
                project.id,
                payload=AssistantRuleProfileUpdateDTO(
                    enabled=True,
                    content="这个项目统一保持冷峻克制的语气。",
                ),
                owner_id=owner.id,
            )
            payload = _build_turn_request(
                project_id=project.id,
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[
                    AssistantMessageDTO(role="user", content="先帮我看一下上一个版本的问题。"),
                    AssistantMessageDTO(role="assistant", content="上一版的问题是冲突落得太快。"),
                    AssistantMessageDTO(role="user", content="那这一版开头怎么改更稳？"),
                ],
            )
            response = await service.turn(session, payload, owner_id=owner.id)

        assert response.skill_id is None
        assert response.content.startswith("主回复：")
        prompt = tool_provider.requests[0]["prompt"]
        system_prompt = tool_provider.requests[0]["system_prompt"] or ""
        assert "【当前会话历史】" in prompt
        assert "用户：先帮我看一下上一个版本的问题。" in prompt
        assert "助手：上一版的问题是冲突落得太快。" in prompt
        assert "【用户当前消息】" in prompt
        assert "那这一版开头怎么改更稳？" in prompt
        assert "【用户长期规则】" in system_prompt
        assert "回答时先给一句方向判断。" in system_prompt
        assert "【当前项目规则】" in system_prompt
        assert "这个项目统一保持冷峻克制的语气。" in system_prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_resolves_recursive_rule_includes_in_stable_order(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-rule-include-order")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        user_rule_root = tmp_path / "assistant-config" / "users" / str(owner_id)
        _write_rule_markdown(
            user_rule_root / "AGENTS.md",
            """
            ---
            enabled: true
            scope: user
            include:
              - fragments/style.md
              - fragments/format.md
            ---

            先给结论。
            """,
        )
        _write_rule_markdown(
            user_rule_root / "fragments" / "style.md",
            """
            ---
            scope: user
            include:
              - nested/tone.md
            ---

            统一保持简洁。
            """,
        )
        _write_rule_markdown(
            user_rule_root / "fragments" / "nested" / "tone.md",
            "若给建议，先给一句判断。",
        )
        _write_rule_markdown(user_rule_root / "fragments" / "format.md", "避免使用表格。")

        async with async_session_factory() as session:
            payload = _build_turn_request(
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[AssistantMessageDTO(role="user", content="帮我改一下开头方向。")],
            )
            await service.turn(session, payload, owner_id=owner_id)

        system_prompt = tool_provider.requests[0]["system_prompt"] or ""
        first = system_prompt.index("先给结论。")
        second = system_prompt.index("统一保持简洁。")
        third = system_prompt.index("若给建议，先给一句判断。")
        fourth = system_prompt.index("避免使用表格。")
        assert first < second < third < fourth
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


@pytest.mark.parametrize(
    ("scope_name", "writer", "message"),
    [
        (
            "missing",
            lambda root, owner_id: _write_rule_markdown(
                root / "AGENTS.md",
                """
                ---
                enabled: true
                scope: user
                include:
                  - fragments/missing.md
                ---

                先给结论。
                """,
            ),
            "does not exist",
        ),
        (
            "cycle",
            lambda root, owner_id: (
                _write_rule_markdown(
                    root / "AGENTS.md",
                    """
                    ---
                    enabled: true
                    scope: user
                    include:
                      - fragments/style.md
                    ---

                    先给结论。
                    """,
                ),
                _write_rule_markdown(
                    root / "fragments" / "style.md",
                    """
                    ---
                    scope: user
                    include:
                      - ../AGENTS.md
                    ---

                    统一保持简洁。
                    """,
                ),
            ),
            "cycle detected",
        ),
        (
            "illegal-scope",
            lambda root, owner_id: _write_rule_markdown(
                root / "AGENTS.md",
                f"""
                ---
                enabled: true
                scope: user
                include:
                  - ../../projects/{uuid.uuid4()}/AGENTS.md
                ---

                先给结论。
                """,
            ),
            "must stay within user scope root",
        ),
    ],
)
async def test_assistant_service_rejects_invalid_rule_includes(
    tmp_path,
    scope_name,
    writer,
    message,
) -> None:
    del scope_name
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=_FakeToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-rule-include-errors")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        user_rule_root = tmp_path / "assistant-config" / "users" / str(owner_id)
        writer(user_rule_root, owner_id)

        async with async_session_factory() as session:
            payload = _build_turn_request(
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[AssistantMessageDTO(role="user", content="帮我改一下开头方向。")],
            )
            with pytest.raises(ConfigurationError, match=message):
                await service.turn(session, payload, owner_id=owner_id)
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def test_assistant_turn_request_rejects_system_messages() -> None:
    with pytest.raises(ValidationError):
        AssistantTurnRequestDTO(
            conversation_id="conversation-invalid",
            client_turn_id="turn-invalid-1",
            model={"provider": "openai", "name": "gpt-4o-mini"},
            messages=[AssistantMessageDTO(role="system", content="你必须先给结论。")],
            requested_write_scope="disabled",
        )


async def test_assistant_service_applies_user_model_preferences(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(
            project_service=create_project_service(),
            config_store=assistant_store,
            credential_service_factory=_FakeCredentialService,
        ),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-preferences")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            await service.assistant_preferences_service.update_preferences(
                session,
                owner.id,
                AssistantPreferencesUpdateDTO(
                    default_provider="openai",
                    default_model_name="gpt-5.4",
                    default_reasoning_effort="high",
                ),
            )
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                messages=[AssistantMessageDTO(role="user", content="给我一个故事方向。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        model = tool_provider.requests[0]["model"]
        assert isinstance(model, dict)
        assert model["provider"] == "openai"
        assert model["name"] == "gpt-5.4"
        assert model["reasoning_effort"] == "high"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_project_preferences_override_user_preferences(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(
            project_service=create_project_service(),
            config_store=assistant_store,
            credential_service_factory=_FakeCredentialService,
        ),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-preferences")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            await service.assistant_preferences_service.update_user_preferences(
                session,
                owner_id=owner.id,
                payload=AssistantPreferencesUpdateDTO(
                    default_provider="gemini",
                    default_model_name="gemini-2.5-flash",
                    default_max_output_tokens=8192,
                    default_thinking_budget=0,
                ),
            )
            await service.assistant_preferences_service.update_project_preferences(
                session,
                project.id,
                owner_id=owner.id,
                payload=AssistantPreferencesUpdateDTO(
                    default_provider="openai",
                    default_model_name="gpt-5.4",
                    default_max_output_tokens=6144,
                    default_reasoning_effort="medium",
                ),
            )
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                project_id=project.id,
                messages=[AssistantMessageDTO(role="user", content="给我一个故事方向。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        model = tool_provider.requests[0]["model"]
        assert isinstance(model, dict)
        assert model["provider"] == "openai"
        assert model["name"] == "gpt-5.4"
        assert model["max_tokens"] == 6144
        assert model["reasoning_effort"] == "medium"
        assert "thinking_budget" not in model
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_clears_stale_provider_native_reasoning_when_target_changes(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(
            project_service=create_project_service(),
            config_store=assistant_store,
            credential_service_factory=_FakeCredentialService,
        ),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-clear-stale-reasoning")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            await service.assistant_preferences_service.update_user_preferences(
                session,
                owner_id=owner.id,
                payload=AssistantPreferencesUpdateDTO(
                    default_provider="gemini",
                    default_model_name="gemini-2.5-flash",
                    default_thinking_budget=0,
                ),
            )
            await service.assistant_preferences_service.update_project_preferences(
                session,
                project.id,
                owner_id=owner.id,
                payload=AssistantPreferencesUpdateDTO(
                    default_provider="openai",
                    default_model_name="gpt-4.1",
                ),
            )
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                project_id=project.id,
                messages=[AssistantMessageDTO(role="user", content="给我一个故事方向。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        model = tool_provider.requests[0]["model"]
        assert isinstance(model, dict)
        assert model["provider"] == "openai"
        assert model["name"] == "gpt-4.1"
        assert "thinking_budget" not in model
        assert "thinking_level" not in model
        assert "reasoning_effort" not in model
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_passes_credential_interop_profile_to_llm_provider(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(
            project_service=create_project_service(),
            config_store=assistant_store,
        ),
        config_loader=loader,
        credential_service_factory=_InteropProfileCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-interop-profile")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                messages=[AssistantMessageDTO(role="user", content="给我一个故事方向。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        credential = tool_provider.requests[0]["credential"]
        assert isinstance(credential, dict)
        assert credential["interop_profile"] == "chat_compat_reasoning_content"
        assert credential["api_dialect"] == "openai_chat_completions"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_structured_agent_hook_after_response(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    _write_yaml(
        config_root / "skills" / "assistant" / "hook-structured-summary.yaml",
        """
skill:
  id: "skill.assistant.hook_structured_summary"
  name: "结构化 Hook 摘要"
  category: "assistant"
  prompt: |
    请输出结构化摘要：
    {{ content }}
  variables:
    content:
      type: "string"
      required: true
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        config_root / "agents" / "writers" / "hook-structured-summary.yaml",
        """
agent:
  id: "agent.hook_structured_summary"
  name: "结构化 Hook 摘要助手"
  type: "checker"
  system_prompt: "你负责把回复整理成结构化摘要。"
  skills: ["skill.assistant.hook_structured_summary"]
  output_schema:
    type: "object"
    properties:
      summary:
        type: "string"
      sentiment:
        type: "string"
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        config_root / "hooks" / "after-structured-summary-agent.yaml",
        """
hook:
  id: "hook.after_structured_summary_agent"
  name: "生成结构化摘要"
  trigger:
    event: "after_assistant_response"
  action:
    type: "agent"
    config:
      agent_id: "agent.hook_structured_summary"
      input_mapping:
        content: "response.content"
""",
    )
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-structured-hook")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                skill_id="skill.assistant.general_chat",
                hook_ids=["hook.after_structured_summary_agent"],
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[AssistantMessageDTO(role="user", content="帮我整理一下今天的新闻。")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.content.startswith("主回复：")
        assert response.hook_results[0].result == {
            "summary": "今天的新闻聚焦科技与国际局势。",
            "sentiment": "neutral",
        }
        structured_call = next(
            item for item in tool_provider.requests if "请输出结构化摘要" in item["prompt"]
        )
        assert structured_call["response_format"] == "json_object"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_rejects_mcp_hook_when_server_disabled(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    _write_yaml(
        config_root / "mcp_servers" / "news.yaml",
        """
mcp_server:
  id: "mcp.news.lookup"
  name: "新闻检索 MCP"
  transport: "streamable_http"
  url: "https://example.com/mcp"
  enabled: false
""",
    )
    loader = ConfigLoader(config_root)
    mcp_tool_caller = _FakeMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=_FakeToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        config_loader=loader,
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-disabled")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                agent_id="agent.general_assistant",
                hook_ids=["hook.before_news_lookup"],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            with pytest.raises(ConfigurationError, match="disabled"):
                await service.turn(session, payload, owner_id=owner_id)
        assert mcp_tool_caller.calls == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_surfaces_mcp_is_error(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    mcp_tool_caller = _ErrorMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=_FakeToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        config_loader=loader,
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-error")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = _build_turn_request(
                agent_id="agent.general_assistant",
                hook_ids=["hook.before_news_lookup"],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            with pytest.raises(RuntimeError, match="is_error=true"):
                await service.turn(session, payload, owner_id=owner_id)
        assert mcp_tool_caller.calls == [
            ("mcp.news.lookup", "search_news", {"query": "今天有什么新闻？"})
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
