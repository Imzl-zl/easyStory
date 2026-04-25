from __future__ import annotations

from app.modules.assistant.service import (
    AssistantMcpCreateDTO,
    AssistantMcpService,
    AssistantMcpUpdateDTO,
)
from app.modules.assistant.service.mcp.assistant_mcp_file_store import AssistantMcpFileStore
from app.modules.config_registry import ConfigLoader
from app.modules.project.service import create_project_service
from app.shared.runtime.errors import BusinessRuleError
from app.shared.settings import ALLOW_PRIVATE_MCP_ENDPOINTS_ENV, clear_settings_cache
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories
from tests.unit.models.helpers import create_project, create_user
from tests.unit.test_assistant_service import _build_config_root


async def test_assistant_mcp_service_creates_updates_resolves_and_deletes_user_mcp(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created = await service.create_user_mcp_server(
                session,
                AssistantMcpCreateDTO(
                    name="资料检索",
                    description="给 Hook 调用的个人外部工具",
                    url="https://example.com/user-mcp",
                    headers={"X-Test": "demo"},
                ),
                owner_id=owner.id,
            )
            updated = await service.update_user_mcp_server(
                session,
                created.id,
                AssistantMcpUpdateDTO(
                    name="资料检索",
                    description="更新后的说明",
                    enabled=False,
                    version=created.version,
                    transport=created.transport,
                    url="https://example.com/user-mcp/v2",
                    headers={"X-Test": "demo-2"},
                    timeout=45,
                ),
                owner_id=owner.id,
            )
            listed = await service.list_user_mcp_servers(session, owner_id=owner.id)
            resolved_disabled = service.resolve_mcp_server(
                created.id,
                owner_id=owner.id,
                allow_disabled=True,
            )
            try:
                service.resolve_mcp_server(created.id, owner_id=owner.id)
            except BusinessRuleError as exc:
                assert "已停用" in str(exc)
            else:
                raise AssertionError("expected disabled user mcp resolution to fail")
            await service.delete_user_mcp_server(session, created.id, owner_id=owner.id)

        assert created.id.startswith("mcp.user.")
        assert created.header_count == 1
        assert updated.enabled is False
        assert updated.timeout == 45
        assert listed[0].id == created.id
        assert resolved_disabled.url == "https://example.com/user-mcp/v2"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_mcp_service_creates_lists_and_resolves_project_mcp(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-mcp-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            created = await service.create_project_mcp_server(
                session,
                project.id,
                AssistantMcpCreateDTO(
                    name="项目资料检索",
                    url="https://example.com/project-mcp",
                    headers={"X-Test": "project"},
                ),
                owner_id=owner.id,
            )
            listed = await service.list_project_mcp_servers(
                session,
                project.id,
                owner_id=owner.id,
            )
            resolved = service.resolve_mcp_server(
                created.id,
                owner_id=owner.id,
                project_id=project.id,
            )

        assert created.id.startswith("mcp.project.")
        assert listed[0].id == created.id
        assert resolved.url == "https://example.com/project-mcp"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_mcp_service_allows_explicit_override_id_for_project_scope(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-mcp-override")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            created = await service.create_project_mcp_server(
                session,
                project.id,
                AssistantMcpCreateDTO(
                    id="mcp.news.lookup",
                    name="项目新闻检索",
                    url="https://example.com/project-mcp",
                    headers={"X-Test": "project"},
                ),
                owner_id=owner.id,
            )
            resolved = service.resolve_mcp_server(
                "mcp.news.lookup",
                owner_id=owner.id,
                project_id=project.id,
            )

        assert created.id == "mcp.news.lookup"
        assert resolved.name == "项目新闻检索"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_mcp_service_rejects_private_mcp_url(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(ALLOW_PRIVATE_MCP_ENDPOINTS_ENV, raising=False)
    clear_settings_cache()
    config_root = _build_config_root(tmp_path)
    service = AssistantMcpService(
        config_loader=ConfigLoader(config_root),
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-private-url")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            try:
                await service.create_user_mcp_server(
                    session,
                    AssistantMcpCreateDTO(
                        name="本地 MCP",
                        url="http://localhost:8765/mcp",
                    ),
                    owner_id=owner.id,
                )
            except BusinessRuleError as exc:
                assert "Private or local MCP endpoints are disabled" in str(exc)
            else:
                raise AssertionError("expected private MCP URL to fail")
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_mcp_service_allows_private_mcp_url_when_enabled(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MCP_ENDPOINTS_ENV, "true")
    clear_settings_cache()
    config_root = _build_config_root(tmp_path)
    service = AssistantMcpService(
        config_loader=ConfigLoader(config_root),
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-private-url-enabled")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created = await service.create_user_mcp_server(
                session,
                AssistantMcpCreateDTO(
                    name="本地 MCP",
                    url="http://localhost:8765/mcp",
                ),
                owner_id=owner.id,
            )

        assert created.url == "http://localhost:8765/mcp"
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
