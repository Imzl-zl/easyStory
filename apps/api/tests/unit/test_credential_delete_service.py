from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.modules.billing.models import TokenUsage
from app.modules.credential.models import ModelCredential
from app.modules.credential.service import (
    CREDENTIAL_DELETE_IN_USE_MESSAGE,
    create_credential_service,
)
from app.modules.observability.models import AuditLog
from app.shared.runtime.errors import BusinessRuleError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user

TEST_MASTER_KEY = "credential-master-key-for-tests"


def test_delete_unused_credential_removes_record_and_writes_audit(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    credential = _create_credential(db, owner_type="user", owner_id=owner.id)
    service = create_credential_service()

    asyncio.run(
        service.delete_credential(
            async_db(db),
            credential.id,
            actor_user_id=owner.id,
        )
    )

    assert db.get(ModelCredential, credential.id) is None
    delete_audit = db.query(AuditLog).filter(AuditLog.event_type == "credential_delete").one()
    assert delete_audit.entity_id == credential.id
    assert delete_audit.details is not None
    assert delete_audit.details["owner_type"] == "user"


def test_delete_used_credential_raises_business_rule_and_keeps_record(
    db,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    project = create_project(db, owner=owner)
    credential = _create_credential(db, owner_type="project", owner_id=project.id)
    _create_token_usage(db, project_id=project.id, credential_id=credential.id)
    service = create_credential_service()

    with pytest.raises(BusinessRuleError, match=CREDENTIAL_DELETE_IN_USE_MESSAGE):
        asyncio.run(
            service.delete_credential(
                async_db(db),
                credential.id,
                actor_user_id=owner.id,
            )
        )

    assert db.get(ModelCredential, credential.id) is not None
    assert (
        db.query(AuditLog).filter(AuditLog.event_type == "credential_delete").count() == 0
    )


def _create_credential(db, *, owner_type: str, owner_id):
    credential = ModelCredential(
        owner_type=owner_type,
        owner_id=owner_id,
        provider="openai",
        display_name=f"{owner_type}-credential",
        encrypted_key=f"ciphertext-{owner_type}",
        is_active=True,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def _create_token_usage(db, *, project_id, credential_id) -> None:
    db.add(
        TokenUsage(
            project_id=project_id,
            node_execution_id=None,
            credential_id=credential_id,
            usage_type="generate",
            model_name="gpt-4.1",
            input_tokens=10,
            output_tokens=20,
            estimated_cost=Decimal("0.001000"),
        )
    )
    db.commit()
