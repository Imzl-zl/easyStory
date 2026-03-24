from __future__ import annotations

import uuid

from app.modules.observability.models import ExecutionLog, PromptReplay
from app.modules.workflow.models import NodeExecution
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import (
    TEST_JWT_SECRET,
    auth_headers as _auth_headers,
    build_runtime_app as _build_runtime_app,
    seed_workflow_project as _seed_project,
)


async def test_workflow_observability_api_filters_query_surfaces(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="observability-query-api")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    app = _build_runtime_app(session_factory, async_session_factory)
    headers = _auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            start_response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=headers,
            )
            execution_id = start_response.json()["execution_id"]

            resume_response = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert resume_response.status_code == 200

        with session_factory() as session:
            workflow_uuid = uuid.UUID(execution_id)
            chapter_split = (
                session.query(NodeExecution)
                .filter(
                    NodeExecution.workflow_execution_id == workflow_uuid,
                    NodeExecution.node_id == "chapter_split",
                )
                .one()
            )
            chapter_gen = (
                session.query(NodeExecution)
                .filter(
                    NodeExecution.workflow_execution_id == workflow_uuid,
                    NodeExecution.node_id == "chapter_gen",
                )
                .one()
            )
            session.add_all(
                [
                    ExecutionLog(
                        workflow_execution_id=workflow_uuid,
                        node_execution_id=chapter_split.id,
                        level="INFO",
                        message="Split detail",
                    ),
                    ExecutionLog(
                        workflow_execution_id=workflow_uuid,
                        node_execution_id=chapter_gen.id,
                        level="ERROR",
                        message="Gen detail",
                    ),
                    PromptReplay(
                        node_execution_id=chapter_gen.id,
                        replay_type="fix",
                        model_name="gpt-4o",
                        prompt_text="fix prompt",
                        response_text="fix正文",
                    ),
                ]
            )
            session.commit()
            chapter_gen_id = chapter_gen.id

        async with started_async_client(app) as client:
            executions_response = await client.get(
                f"/api/v1/workflows/{execution_id}/executions",
                params={"node_id": "chapter_gen", "status": "completed"},
                headers=headers,
            )
            assert executions_response.status_code == 200
            executions = executions_response.json()
            assert [(item["node_id"], item["status"]) for item in executions] == [
                ("chapter_gen", "completed")
            ]

            logs_response = await client.get(
                f"/api/v1/workflows/{execution_id}/logs",
                params={"node_execution_id": str(chapter_gen_id)},
                headers=headers,
            )
            assert logs_response.status_code == 200
            logs = logs_response.json()
            assert logs
            assert all(item["node_execution_id"] == str(chapter_gen_id) for item in logs)
            assert "Gen detail" in [item["message"] for item in logs]
            assert "Split detail" not in [item["message"] for item in logs]

            replays_response = await client.get(
                f"/api/v1/workflows/{execution_id}/node-executions/{chapter_gen_id}/prompt-replays",
                params={"replay_type": "fix"},
                headers=headers,
            )
            assert replays_response.status_code == 200
            replays = replays_response.json()
            assert [item["replay_type"] for item in replays] == ["fix"]
            assert replays[0]["response_text"] == "fix正文"

            async with client.stream(
                "GET",
                f"/api/v1/workflows/{execution_id}/events",
                params={
                    "node_execution_id": str(chapter_gen_id),
                    "timeout_seconds": 1,
                    "poll_interval_ms": 100,
                },
                headers=headers,
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert "Gen detail" in body
        assert "Split detail" not in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
