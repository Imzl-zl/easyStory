from __future__ import annotations

import asyncio
import json
import shutil

from app.modules.credential.service.credential_service_support import ResolvedCredentialModel
from tests.unit.test_workflow_runtime import _list_node_executions
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


def test_runtime_chapter_split_falls_back_to_next_model(db) -> None:
    harness = _build_runtime_harness(db)
    harness.runtime_service.tool_provider = _ChapterSplitFallbackToolProvider(fail_models={"gpt-4o"})
    harness.workflow.workflow_snapshot["model_fallback"] = {
        "enabled": True,
        "chain": [{"model": "deepseek-v3"}],
        "on_all_fail": "pause",
    }
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)

        assert harness.workflow.status == "paused"
        assert harness.workflow.resume_from_node == "chapter_gen"
        assert harness.runtime_service.tool_provider.model_names == ["gpt-4o", "deepseek-v3"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_chapter_split_pauses_when_fallback_chain_exhausted(db) -> None:
    harness = _build_runtime_harness(db)
    harness.runtime_service.tool_provider = _ChapterSplitFallbackToolProvider(
        fail_models={"gpt-4o", "deepseek-v3"}
    )
    harness.workflow.workflow_snapshot["model_fallback"] = {
        "enabled": True,
        "chain": [{"model": "deepseek-v3"}],
        "on_all_fail": "pause",
    }
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)
        node_executions = _list_node_executions(db, harness.workflow.id)

        assert harness.workflow.status == "paused"
        assert harness.workflow.pause_reason == "model_fallback_exhausted"
        assert harness.workflow.snapshot["pending_actions"][0]["type"] == "model_fallback_exhausted"
        assert [item.status for item in node_executions] == ["failed"]
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_chapter_split_fails_when_fallback_chain_policy_is_fail(db) -> None:
    harness = _build_runtime_harness(db)
    harness.runtime_service.tool_provider = _ChapterSplitFallbackToolProvider(
        fail_models={"gpt-4o", "deepseek-v3"}
    )
    harness.workflow.workflow_snapshot["model_fallback"] = {
        "enabled": True,
        "chain": [{"model": "deepseek-v3"}],
        "on_all_fail": "fail",
    }
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)

        assert harness.workflow.status == "failed"
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_chapter_split_rejects_unverifiable_required_capabilities(db) -> None:
    harness = _build_runtime_harness(db)
    harness.runtime_service.tool_provider = _ChapterSplitFallbackToolProvider()
    harness.workflow.workflow_snapshot["model_fallback"] = {
        "enabled": True,
        "chain": [{"model": "deepseek-v3"}],
        "on_all_fail": "pause",
    }
    harness.workflow.skills_snapshot["skill.chapter_split.default"]["model"]["required_capabilities"] = [
        "unknown_capability"
    ]
    try:
        asyncio.run(harness.runtime_service.run(async_db(db), harness.workflow, owner_id=harness.owner_id))
        db.commit()
        db.refresh(harness.workflow)

        assert harness.workflow.status == "paused"
        assert harness.workflow.pause_reason == "model_fallback_exhausted"
        assert harness.runtime_service.tool_provider.model_names == []
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


class _ChapterSplitFallbackToolProvider:
    def __init__(self, *, fail_models: set[str] | None = None) -> None:
        self.fail_models = fail_models or set()
        self.model_names: list[str] = []

    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        model_name = params["model"].get("name")
        if model_name is not None:
            self.model_names.append(model_name)
        if model_name in self.fail_models:
            raise RuntimeError(f"upstream failed for {model_name}")
        return {
            "content": json.dumps(
                {
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "title": "第一章 逃亡夜",
                            "brief": "主角连夜出逃并暴露追兵",
                            "key_characters": ["林渊"],
                            "key_events": ["夜逃"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            "model_name": model_name,
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }

    def list_tools(self) -> list[str]:
        return ["llm.generate"]
