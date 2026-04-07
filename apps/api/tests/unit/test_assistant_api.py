from __future__ import annotations

from app.main import create_app
from app.modules.assistant.entry.http.router import get_assistant_service
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories, started_async_client
from tests.unit.models.helpers import create_user
from tests.unit.test_assistant_service import (
    _FakeCredentialService,
    _FakeMcpToolCaller,
    _FakeToolProvider,
    _build_config_root,
)
from app.modules.assistant.service.factory import create_assistant_rule_service
from app.modules.assistant.service.hooks_runtime.assistant_hook_providers import (
    build_assistant_plugin_registry,
)
from app.modules.assistant.service.assistant_runtime_terminal import (
    AssistantRuntimeTerminalError,
    attach_assistant_stream_error_meta,
)
from app.modules.assistant.service.assistant_service import AssistantService, AssistantStreamEvent
from app.modules.assistant.service.turn.assistant_turn_run_store import AssistantTurnRunStore
from app.modules.config_registry import ConfigLoader
from app.modules.project.service import create_project_service
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.provider_interop_stream_support import StreamInterruptedError


async def test_assistant_api_requires_auth_and_returns_content(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        config_root = _build_config_root(tmp_path)
        loader = ConfigLoader(config_root)
        tool_provider = _FakeToolProvider()
        turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
        service = AssistantService(
            assistant_rule_service=create_assistant_rule_service(),
            config_loader=loader,
            credential_service_factory=_FakeCredentialService,
            project_service=create_project_service(),
            tool_provider=tool_provider,
            template_renderer=SkillTemplateRenderer(),
            turn_run_store=turn_run_store,
        )
        service.plugin_registry = build_assistant_plugin_registry(
            service,
            config_loader=loader,
            mcp_tool_caller=_FakeMcpToolCaller(),
        )
        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: service

        async with started_async_client(app) as client:
            unauthorized = await client.post(
                "/api/v1/assistant/turn",
                json={
                    "conversation_id": "conversation-api-unauthorized",
                    "client_turn_id": "turn-api-unauthorized-1",
                    "skill_id": "skill.assistant.general_chat",
                    "model": {"provider": "openai", "name": "gpt-4o-mini"},
                    "messages": [{"role": "user", "content": "今天有什么新闻？"}],
                    "requested_write_scope": "disabled",
                },
            )
            authorized = await client.post(
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-authorized",
                    "client_turn_id": "turn-api-authorized-1",
                    "agent_id": "agent.general_assistant",
                    "hook_ids": ["hook.before_news_lookup"],
                    "stream": False,
                    "messages": [{"role": "user", "content": "今天有什么新闻？"}],
                    "requested_write_scope": "disabled",
                },
            )

        assert unauthorized.status_code == 401
        assert authorized.status_code == 200
        body = authorized.json()
        assert body["content"].startswith("主回复：")
        assert body["skill_id"] == "skill.assistant.general_chat"
        assert body["hook_results"][0]["action_type"] == "mcp"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_stream_turn_returns_sse_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-stream")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        config_root = _build_config_root(tmp_path)
        loader = ConfigLoader(config_root)
        tool_provider = _FakeToolProvider()
        turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
        service = AssistantService(
            assistant_rule_service=create_assistant_rule_service(),
            config_loader=loader,
            credential_service_factory=_FakeCredentialService,
            project_service=create_project_service(),
            tool_provider=tool_provider,
            template_renderer=SkillTemplateRenderer(),
            turn_run_store=turn_run_store,
        )
        service.plugin_registry = build_assistant_plugin_registry(
            service,
            config_loader=loader,
            mcp_tool_caller=_FakeMcpToolCaller(),
        )
        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: service

        async with started_async_client(app) as client:
            async with client.stream(
                "POST",
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-stream",
                    "client_turn_id": "turn-api-stream-1",
                    "skill_id": "skill.assistant.general_chat",
                    "stream": True,
                    "messages": [{"role": "user", "content": "给我一个故事方向。"}],
                    "requested_write_scope": "disabled",
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert "event: run_started" in body
        assert "event: chunk" in body
        assert "event: completed" in body
        assert "主回复：" in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_turn_returns_conversation_state_mismatch_code(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-continuation-mismatch")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        config_root = _build_config_root(tmp_path)
        loader = ConfigLoader(config_root)
        tool_provider = _FakeToolProvider()
        turn_run_store = AssistantTurnRunStore(tmp_path / "turn-runs")
        service = AssistantService(
            assistant_rule_service=create_assistant_rule_service(),
            config_loader=loader,
            credential_service_factory=_FakeCredentialService,
            project_service=create_project_service(),
            tool_provider=tool_provider,
            template_renderer=SkillTemplateRenderer(),
            turn_run_store=turn_run_store,
        )
        service.plugin_registry = build_assistant_plugin_registry(
            service,
            config_loader=loader,
            mcp_tool_caller=_FakeMcpToolCaller(),
        )
        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: service

        async with started_async_client(app) as client:
            first_response = await client.post(
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-continuation-mismatch",
                    "client_turn_id": "turn-api-continuation-mismatch-1",
                    "stream": False,
                    "skill_id": "skill.assistant.general_chat",
                    "messages": [{"role": "user", "content": "先给我一个方向。"}],
                    "requested_write_scope": "disabled",
                },
            )
            assert first_response.status_code == 200
            first_body = first_response.json()

            mismatch_response = await client.post(
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-continuation-mismatch",
                    "client_turn_id": "turn-api-continuation-mismatch-2",
                    "stream": False,
                    "skill_id": "skill.assistant.general_chat",
                    "continuation_anchor": {
                        "previous_run_id": first_body["run_id"],
                    },
                    "messages": [
                        {"role": "user", "content": "先给我一个方向。"},
                        {"role": "assistant", "content": "被篡改的上一轮回复"},
                        {"role": "user", "content": "继续往下展开。"},
                    ],
                    "requested_write_scope": "disabled",
                },
            )

        assert mismatch_response.status_code == 422
        assert mismatch_response.json() == {
            "code": "conversation_state_mismatch",
            "detail": "当前会话状态已变化，请刷新对话后重试。",
        }
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_stream_turn_returns_structured_error_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-stream-error")
    )

    class _ErroringAssistantService:
        async def stream_turn(self, db, payload, *, owner_id, should_stop=None):
            del db, payload, owner_id, should_stop
            raise AssistantRuntimeTerminalError(
                code="tool_loop_exhausted",
                message="本轮工具调用次数已达上限，已停止继续执行。",
                terminal_status="failed",
                write_effective=False,
            )
            yield  # pragma: no cover

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: _ErroringAssistantService()

        async with started_async_client(app) as client:
            async with client.stream(
                "POST",
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-stream-error",
                    "client_turn_id": "turn-api-stream-error-1",
                    "stream": True,
                    "messages": [{"role": "user", "content": "继续。"}],
                    "requested_write_scope": "disabled",
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert "event: error" in body
        assert '"run_id": "' in body
        assert '"conversation_id": "conversation-api-stream-error"' in body
        assert '"client_turn_id": "turn-api-stream-error-1"' in body
        assert '"event_seq": 1' in body
        assert '"state_version": 1' in body
        assert '"message": "本轮工具调用次数已达上限，已停止继续执行。"' in body
        assert '"code": "tool_loop_exhausted"' in body
        assert '"terminal_status": "failed"' in body
        assert '"write_effective": false' in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_stream_turn_returns_cancelled_error_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-stream-cancelled")
    )

    class _CancelledAssistantService:
        async def stream_turn(self, db, payload, *, owner_id, should_stop=None):
            del db, payload, owner_id, should_stop
            raise StreamInterruptedError("client disconnected during streaming")
            yield  # pragma: no cover

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: _CancelledAssistantService()

        async with started_async_client(app) as client:
            async with client.stream(
                "POST",
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-stream-cancelled",
                    "client_turn_id": "turn-api-stream-cancelled-1",
                    "stream": True,
                    "messages": [{"role": "user", "content": "停止。"}],
                    "requested_write_scope": "disabled",
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert "event: error" in body
        assert '"run_id": "' in body
        assert '"conversation_id": "conversation-api-stream-cancelled"' in body
        assert '"client_turn_id": "turn-api-stream-cancelled-1"' in body
        assert '"event_seq": 1' in body
        assert '"state_version": 1' in body
        assert '"message": "本轮已停止。"' in body
        assert '"code": "cancel_requested"' in body
        assert '"terminal_status": "cancelled"' in body
        assert '"write_effective": false' in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_stream_turn_returns_cancelled_write_effective_error_payload(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-stream-cancelled-write-effective")
    )

    class _CancelledAfterCommittedWriteAssistantService:
        async def stream_turn(self, db, payload, *, owner_id, should_stop=None):
            del db, payload, owner_id, should_stop
            raise AssistantRuntimeTerminalError(
                code="cancel_requested",
                message="本轮已停止，但已有写入生效。",
                terminal_status="cancelled",
                write_effective=True,
            )
            yield  # pragma: no cover

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = (
            lambda: _CancelledAfterCommittedWriteAssistantService()
        )

        async with started_async_client(app) as client:
            async with client.stream(
                "POST",
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-stream-cancelled-write-effective",
                    "client_turn_id": "turn-api-stream-cancelled-write-effective-1",
                    "stream": True,
                    "messages": [{"role": "user", "content": "停止。"}],
                    "requested_write_scope": "disabled",
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert "event: error" in body
        assert '"run_id": "' in body
        assert '"conversation_id": "conversation-api-stream-cancelled-write-effective"' in body
        assert '"client_turn_id": "turn-api-stream-cancelled-write-effective-1"' in body
        assert '"event_seq": 1' in body
        assert '"state_version": 1' in body
        assert '"message": "本轮已停止，但已有写入生效。"' in body
        assert '"code": "cancel_requested"' in body
        assert '"terminal_status": "cancelled"' in body
        assert '"write_effective": true' in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_stream_turn_preserves_nested_terminal_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-stream-nested-terminal")
    )

    class _NestedTerminalAssistantService:
        async def stream_turn(self, db, payload, *, owner_id, should_stop=None):
            del db, payload, owner_id, should_stop
            raise ExceptionGroup(
                "Assistant runtime error and on_error hook both failed",
                [
                    AssistantRuntimeTerminalError(
                        code="committed_state_persist_failed",
                        message="文稿写入已生效，但运行时未能完成 committed 状态落盘。",
                        terminal_status="failed",
                        write_effective=True,
                    ),
                    RuntimeError("on_error hook failed"),
                ],
            )
            yield  # pragma: no cover

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: _NestedTerminalAssistantService()

        async with started_async_client(app) as client:
            async with client.stream(
                "POST",
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-stream-nested-terminal",
                    "client_turn_id": "turn-api-stream-nested-terminal-1",
                    "stream": True,
                    "messages": [{"role": "user", "content": "继续。"}],
                    "requested_write_scope": "disabled",
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert "event: error" in body
        assert '"run_id": "' in body
        assert '"conversation_id": "conversation-api-stream-nested-terminal"' in body
        assert '"client_turn_id": "turn-api-stream-nested-terminal-1"' in body
        assert '"event_seq": 1' in body
        assert '"state_version": 1' in body
        assert '"message": "文稿写入已生效，但运行时未能完成 committed 状态落盘。"' in body
        assert '"code": "committed_state_persist_failed"' in body
        assert '"terminal_status": "failed"' in body
        assert '"write_effective": true' in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_stream_turn_prefers_attached_stream_error_meta(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-stream-error-meta")
    )

    class _ErroringAfterRunStartedAssistantService:
        async def stream_turn(self, db, payload, *, owner_id, should_stop=None):
            del db, payload, owner_id, should_stop
            yield AssistantStreamEvent(
                "run_started",
                {
                    "run_id": "run-attached-1",
                    "conversation_id": "conversation-api-stream-error-meta",
                    "client_turn_id": "turn-api-stream-error-meta-1",
                    "event_seq": 1,
                    "state_version": 1,
                    "ts": "2026-04-06T00:00:00Z",
                    "requested_write_scope": "disabled",
                    "requested_write_targets": [],
                },
            )
            error = AssistantRuntimeTerminalError(
                code="tool_loop_exhausted",
                message="本轮工具调用次数已达上限，已停止继续执行。",
                terminal_status="failed",
                write_effective=False,
            )
            raise attach_assistant_stream_error_meta(
                error,
                {
                    "run_id": "run-attached-1",
                    "conversation_id": "conversation-api-stream-error-meta",
                    "client_turn_id": "turn-api-stream-error-meta-1",
                    "event_seq": 2,
                    "state_version": 2,
                    "ts": "2026-04-06T00:00:01Z",
                },
            )
            yield  # pragma: no cover

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = (
            lambda: _ErroringAfterRunStartedAssistantService()
        )

        async with started_async_client(app) as client:
            async with client.stream(
                "POST",
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "conversation_id": "conversation-api-stream-error-meta",
                    "client_turn_id": "turn-api-stream-error-meta-1",
                    "stream": True,
                    "messages": [{"role": "user", "content": "继续。"}],
                    "requested_write_scope": "disabled",
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert 'event: run_started' in body
        assert '"run_id": "run-attached-1"' in body
        assert '"event_seq": 2' in body
        assert '"state_version": 2' in body
        assert '"message": "本轮工具调用次数已达上限，已停止继续执行。"' in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
