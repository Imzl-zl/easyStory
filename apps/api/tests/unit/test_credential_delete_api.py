from __future__ import annotations

from decimal import Decimal
import uuid

from app.main import create_app
from app.modules.billing.models import TokenUsage
from app.modules.credential.models import ModelCredential
from app.modules.credential.service import CREDENTIAL_DELETE_IN_USE_MESSAGE
from app.modules.project.models import Project
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_user

TEST_MASTER_KEY = "credential-master-key-for-tests"


async def test_credentials_delete_api_removes_unused_credential(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-delete-api-success")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        owner_id, credential_id = _seed_unused_credential(session_factory)

        async with started_async_client(app) as client:
            response = await client.delete(
                f"/api/v1/credentials/{credential_id}",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 204
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_credentials_delete_api_rejects_used_credential(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-delete-api-used")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        owner_id, credential_id = _seed_used_project_credential(session_factory)

        async with started_async_client(app) as client:
            response = await client.delete(
                f"/api/v1/credentials/{credential_id}",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
        assert response.json()["detail"] == CREDENTIAL_DELETE_IN_USE_MESSAGE
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _seed_unused_credential(session_factory) -> tuple[uuid.UUID, str]:
    with session_factory() as session:
        owner = create_user(session)
        credential = ModelCredential(
            owner_type="user",
            owner_id=owner.id,
            provider="openai",
            display_name="unused-user-credential",
            encrypted_key="ciphertext-user",
            is_active=True,
        )
        session.add(credential)
        session.commit()
        session.refresh(credential)
        return owner.id, str(credential.id)


def _seed_used_project_credential(session_factory) -> tuple[uuid.UUID, str]:
    with session_factory() as session:
        owner = create_user(session)
        project = Project(name="Credential Delete API", owner_id=owner.id)
        session.add(project)
        session.commit()
        session.refresh(project)
        credential = ModelCredential(
            owner_type="project",
            owner_id=project.id,
            provider="openai",
            display_name="used-project-credential",
            encrypted_key="ciphertext-project",
            is_active=True,
        )
        session.add(credential)
        session.commit()
        session.refresh(credential)
        session.add(
            TokenUsage(
                project_id=project.id,
                node_execution_id=None,
                credential_id=credential.id,
                usage_type="generate",
                model_name="gpt-4.1",
                input_tokens=10,
                output_tokens=20,
                estimated_cost=Decimal("0.001000"),
            )
        )
        session.commit()
        return owner.id, str(credential.id)
