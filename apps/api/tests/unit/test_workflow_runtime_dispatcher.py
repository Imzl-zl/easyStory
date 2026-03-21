from __future__ import annotations

import asyncio
import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

import app.modules.workflow.entry.http.router as workflow_router
from app.main import create_app
from app.modules.workflow.entry.http.router import get_workflow_runtime_dispatcher
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)


class _FakeWorkflowAppService:
    def __init__(self) -> None:
        self.calls: list[tuple[AsyncSession, uuid.UUID, uuid.UUID]] = []

    async def run_workflow_runtime(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        self.calls.append((db, workflow_id, owner_id))


async def test_runtime_dispatcher_uses_request_async_session_factory(
    monkeypatch,
    tmp_path,
) -> None:
    _, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-dispatcher")
    )
    app = create_app(async_session_factory=async_session_factory)
    request = Request(
        {
            "type": "http",
            "app": app,
            "method": "POST",
            "path": "/api/v1/projects/test/workflows/start",
            "headers": [],
            "query_string": b"",
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
            "http_version": "1.1",
        }
    )
    workflow_app_service = _FakeWorkflowAppService()
    scheduled_tasks: list[asyncio.Task[None]] = []
    original_create_task = asyncio.create_task

    def capture_task(coro) -> asyncio.Task[None]:
        task = original_create_task(coro)
        scheduled_tasks.append(task)
        return task

    monkeypatch.setattr(workflow_router.asyncio, "create_task", capture_task)
    workflow_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    try:
        dispatcher = await get_workflow_runtime_dispatcher(
            request,
            workflow_app_service=workflow_app_service,
        )

        dispatcher(workflow_id, owner_id)

        assert len(scheduled_tasks) == 1
        await scheduled_tasks[0]
        assert len(workflow_app_service.calls) == 1
        session, observed_workflow_id, observed_owner_id = workflow_app_service.calls[0]
        assert isinstance(session, AsyncSession)
        assert observed_workflow_id == workflow_id
        assert observed_owner_id == owner_id
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
