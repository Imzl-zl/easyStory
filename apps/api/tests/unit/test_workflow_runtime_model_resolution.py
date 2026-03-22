from __future__ import annotations

import asyncio
import shutil

from app.modules.credential.service.credential_service_support import ResolvedCredentialModel
from tests.unit.async_service_support import async_db
from tests.unit.test_workflow_runtime import _build_runtime_harness


def test_runtime_generate_step_reuses_resolved_credential(db) -> None:
    harness = _build_runtime_harness(db)
    base_service = harness.runtime_service._resolve_credential_service()
    spy_service = _CredentialResolutionSpy(base_service)
    harness.runtime_service._credential_service = spy_service
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        assert spy_service.model_resolution_calls == 1
        assert spy_service.credential_lookup_calls == 0
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


class _CredentialResolutionSpy:
    def __init__(self, delegate) -> None:
        self._delegate = delegate
        self.crypto = delegate.crypto
        self.model_resolution_calls = 0
        self.credential_lookup_calls = 0

    async def resolve_active_credential(self, *args, **kwargs):
        self.credential_lookup_calls += 1
        return await self._delegate.resolve_active_credential(*args, **kwargs)

    async def resolve_active_credential_model(self, *args, **kwargs):
        self.model_resolution_calls += 1
        credential = await self._delegate.resolve_active_credential(
            *args,
            provider=kwargs["provider"],
            user_id=kwargs["user_id"],
            project_id=kwargs.get("project_id"),
        )
        return ResolvedCredentialModel(
            credential=credential,
            model_name=kwargs["requested_model_name"] or credential.default_model or "gpt-4o-mini",
        )
