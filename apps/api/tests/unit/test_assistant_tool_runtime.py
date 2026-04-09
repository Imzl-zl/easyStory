import asyncio
from concurrent.futures import ThreadPoolExecutor
import dataclasses
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import threading
import uuid

from pydantic import ValidationError
import pytest

from app.modules.assistant.service import (
    AssistantRunBudget,
    AssistantToolPolicyResolver,
    AssistantToolDescriptorRegistry,
    AssistantToolExecutor,
    AssistantToolExposurePolicy,
    AssistantToolLoop,
    AssistantToolLoopModelStreamEvent,
    AssistantToolStepRecord,
    AssistantToolStepStore,
)
from app.modules.assistant.service.assistant_runtime_terminal import AssistantRuntimeTerminalError
from app.modules.assistant.service.dto import build_structured_items_digest
from app.modules.assistant.service.tooling.assistant_tool_loop_output_support import (
    _build_tool_cycle_continuation_items,
)
from app.modules.assistant.service.tooling.assistant_tool_loop_budget_support import (
    apply_tool_loop_request_budget,
)
from app.modules.assistant.service.tooling.assistant_tool_loop_result_support import _build_tool_call_start_payload
from app.modules.assistant.service.tooling.assistant_tool_executor import (
    PROJECT_SEARCH_DOCUMENTS_DEFAULT_LIMIT,
    ProjectReadDocumentsToolArgs,
    ProjectSearchDocumentsToolArgs,
)
from app.modules.assistant.service.tooling.assistant_tool_catalog_support import build_tool_catalog_version
from app.modules.assistant.service.tooling.assistant_tool_runtime_dto import (
    AssistantToolApprovalGrant,
    AssistantToolDescriptor,
    AssistantToolPolicyDecision,
    AssistantToolResultEnvelope,
    AssistantToolExecutionContext,
    AssistantToolExposureContext,
)
from app.modules.project.infrastructure import ProjectDocumentFileStore, ProjectDocumentIdentityStore
from app.modules.project.service import ProjectDocumentCapabilityService, ProjectService
from app.modules.project.service.project_document_buffer_state_support import (
    TRUSTED_ACTIVE_BUFFER_SOURCE,
    build_project_document_buffer_hash,
)
from app.shared.runtime.llm.llm_protocol import resolve_continuation_support
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, ready_project_setting


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


def test_assistant_tool_step_store_appends_and_reads_history(tmp_path):
    store = AssistantToolStepStore(tmp_path / "tool-steps")
    run_id = uuid.uuid4()
    started_at = datetime(2026, 4, 5, tzinfo=UTC)
    base_record = AssistantToolStepRecord(
        run_id=run_id,
        tool_call_id="tool-call-1",
        step_index=1,
        tool_name="project.read_documents",
        descriptor_hash="descriptor-hash",
        normalized_arguments_snapshot={"paths": ["设定/人物.md"]},
        arguments_hash="arguments-hash",
        target_document_refs=(),
        approval_state="not_required",
        approval_grant_id=None,
        status="reading",
        dedupe_key="dedupe-key",
        idempotency_key=None,
        result_summary=None,
        result_hash=None,
        error_code=None,
        started_at=started_at,
        completed_at=None,
    )
    completed_record = dataclasses.replace(
        base_record,
        status="completed",
        target_document_refs=("project_file:1",),
        result_summary={"document_count": 1},
        result_hash="result-hash",
        completed_at=started_at,
    )

    store.append_step(base_record)
    store.append_step(completed_record)

    history = store.list_step_history(run_id, "tool-call-1")

    assert [item.status for item in history] == ["reading", "completed"]
    assert store.get_latest_step(run_id, "tool-call-1") == completed_record
    assert store.list_latest_steps(run_id) == [completed_record]


def test_assistant_tool_step_store_keeps_all_snapshots_under_concurrent_append(tmp_path):
    store = AssistantToolStepStore(tmp_path / "tool-steps")
    run_id = uuid.uuid4()
    started_at = datetime(2026, 4, 5, tzinfo=UTC)
    base_record = AssistantToolStepRecord(
        run_id=run_id,
        tool_call_id="tool-call-1",
        step_index=1,
        tool_name="project.read_documents",
        descriptor_hash="descriptor-hash",
        normalized_arguments_snapshot={"paths": ["设定/人物.md"]},
        arguments_hash="arguments-hash",
        target_document_refs=(),
        approval_state="not_required",
        approval_grant_id=None,
        status="reading",
        dedupe_key="dedupe-key",
        idempotency_key=None,
        result_summary=None,
        result_hash=None,
        error_code=None,
        started_at=started_at,
        completed_at=None,
    )
    worker_count = 8
    barrier = threading.Barrier(worker_count)

    def append_snapshot(index: int) -> None:
        barrier.wait()
        store.append_step(
            dataclasses.replace(
                base_record,
                dedupe_key=f"dedupe-key-{index}",
            )
        )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        list(executor.map(append_snapshot, range(worker_count)))

    history = store.list_step_history(run_id, "tool-call-1")

    assert len(history) == worker_count
    assert {item.dedupe_key for item in history} == {f"dedupe-key-{index}" for index in range(worker_count)}


def test_assistant_tool_step_store_rejects_invalid_literal_fields(tmp_path):
    store = AssistantToolStepStore(tmp_path / "tool-steps")
    run_id = uuid.uuid4()
    step_dir = tmp_path / "tool-steps" / str(run_id) / "tool-call-1"
    step_dir.mkdir(parents=True)
    (step_dir / "0001.json").write_text(
        json.dumps(
            {
                "run_id": str(run_id),
                "tool_call_id": "tool-call-1",
                "step_index": 1,
                "tool_name": "project.read_documents",
                "descriptor_hash": "descriptor-hash",
                "normalized_arguments_snapshot": {"paths": ["设定/人物.md"]},
                "arguments_hash": "arguments-hash",
                "target_document_refs": [],
                "approval_state": "unexpected",
                "approval_grant_id": None,
                "status": "reading",
                "dedupe_key": "dedupe-key",
                "idempotency_key": None,
                "result_summary": None,
                "result_hash": None,
                "error_code": None,
                "started_at": "2026-04-05T00:00:00+00:00",
                "completed_at": None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError) as exc_info:
        store.list_step_history(run_id, "tool-call-1")

    assert "approval_state" in str(exc_info.value)


def test_assistant_tool_descriptor_registry_exposes_project_read_documents_descriptor():
    registry = AssistantToolDescriptorRegistry()

    list_descriptor = registry.get_descriptor("project.list_documents")
    search_descriptor = registry.get_descriptor("project.search_documents")
    descriptor = registry.get_descriptor("project.read_documents")

    assert list_descriptor is not None
    assert list_descriptor.execution_locus == "local_runtime"
    assert list_descriptor.approval_mode == "none"
    assert list_descriptor.plane == "resource"
    assert list_descriptor.mutability == "read_only"
    assert list_descriptor.origin == "project_document"
    assert list_descriptor.trust_class == "local_first_party"

    assert search_descriptor is not None
    assert search_descriptor.execution_locus == "local_runtime"
    assert search_descriptor.approval_mode == "none"
    assert search_descriptor.plane == "resource"
    assert search_descriptor.mutability == "read_only"
    assert search_descriptor.origin == "project_document"
    assert search_descriptor.trust_class == "local_first_party"

    assert descriptor is not None
    assert descriptor.execution_locus == "local_runtime"
    assert descriptor.approval_mode == "none"
    assert descriptor.plane == "resource"
    assert descriptor.mutability == "read_only"
    assert descriptor.origin == "project_document"
    assert descriptor.trust_class == "local_first_party"

    write_descriptor = registry.get_descriptor("project.write_document")

    assert write_descriptor is not None
    assert write_descriptor.execution_locus == "local_runtime"
    assert write_descriptor.approval_mode == "grant_bound"
    assert write_descriptor.plane == "mutation"
    assert write_descriptor.mutability == "write"
    assert write_descriptor.idempotency_class == "conditional_write"


def test_project_read_documents_tool_args_treats_null_cursors_as_empty_list():
    arguments = ProjectReadDocumentsToolArgs.model_validate(
        {
            "paths": ["设定/人物.md"],
            "cursors": None,
        }
    )

    assert arguments.cursors == []


def test_project_search_documents_tool_args_treats_null_optional_filters_as_omitted():
    arguments = ProjectSearchDocumentsToolArgs.model_validate(
        {
            "query": "人物关系",
            "path_prefix": None,
            "sources": None,
            "schema_ids": None,
            "content_states": None,
            "writable": None,
            "limit": None,
        }
    )

    assert arguments.query == "人物关系"
    assert arguments.path_prefix is None
    assert arguments.sources == []
    assert arguments.schema_ids == []
    assert arguments.content_states == []
    assert arguments.writable is None
    assert arguments.limit == PROJECT_SEARCH_DOCUMENTS_DEFAULT_LIMIT


def test_assistant_tool_descriptor_registry_uses_strict_project_document_schemas():
    registry = AssistantToolDescriptorRegistry()

    list_descriptor = registry.get_descriptor("project.list_documents")
    read_descriptor = registry.get_descriptor("project.read_documents")
    write_descriptor = registry.get_descriptor("project.write_document")
    assert list_descriptor is not None
    assert read_descriptor is not None
    assert write_descriptor is not None

    list_documents_schema = list_descriptor.output_schema["properties"]["documents"]
    read_documents_schema = read_descriptor.output_schema["properties"]["documents"]
    diff_summary_schema = write_descriptor.output_schema["properties"]["diff_summary"]

    assert list_documents_schema["items"]["additionalProperties"] is False
    assert "binding_version" in list_documents_schema["items"]["required"]
    assert read_documents_schema["items"]["additionalProperties"] is False
    assert "content" in read_documents_schema["items"]["required"]
    assert diff_summary_schema["additionalProperties"] is False
    assert diff_summary_schema["required"] == ["changed", "previous_chars", "next_chars"]


def test_build_tool_catalog_version_is_order_stable_and_tracks_visible_descriptors():
    registry = AssistantToolDescriptorRegistry()
    list_descriptor = registry.get_descriptor("project.list_documents")
    read_descriptor = registry.get_descriptor("project.read_documents")
    write_descriptor = registry.get_descriptor("project.write_document")
    assert list_descriptor is not None
    assert read_descriptor is not None
    assert write_descriptor is not None

    read_only_version = build_tool_catalog_version((list_descriptor, read_descriptor))
    reordered_version = build_tool_catalog_version((read_descriptor, list_descriptor))
    writable_version = build_tool_catalog_version((list_descriptor, read_descriptor, write_descriptor))

    assert read_only_version.startswith("tool_catalog:")
    assert reordered_version == read_only_version
    assert writable_version != read_only_version


def test_assistant_tool_loop_resolves_minimal_run_budget_from_existing_boundaries():
    registry = AssistantToolDescriptorRegistry()
    policy = AssistantToolExposurePolicy(registry=registry)
    read_descriptor = registry.get_descriptor("project.read_documents")
    write_descriptor = registry.get_descriptor("project.write_document")
    assert read_descriptor is not None
    assert write_descriptor is not None
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=AssistantToolExecutor(project_document_capability_service=object()),
        max_iterations=6,
    )

    budget = loop.resolve_run_budget(
        turn_context=None,
        project_id=uuid.uuid4(),
        visible_descriptors=(read_descriptor,),
    )

    assert budget.max_steps == 6
    assert budget.max_tool_calls == 6
    assert budget.max_parallel_tool_calls == 1
    assert budget.tool_timeout_seconds == 15

    write_budget = loop.resolve_run_budget(
        turn_context=None,
        project_id=uuid.uuid4(),
        visible_descriptors=(read_descriptor, write_descriptor),
    )

    assert write_budget.max_steps == 6
    assert write_budget.max_tool_calls == 6
    assert write_budget.max_parallel_tool_calls == 1
    assert write_budget.tool_timeout_seconds is None


def test_assistant_tool_loop_resolves_policy_bundle_with_budget_snapshot():
    class _RecordingResolver(AssistantToolPolicyResolver):
        def __init__(self) -> None:
            self.budget_snapshots: list[dict[str, object] | None] = []

        def resolve(self, *, descriptor, context) -> AssistantToolPolicyDecision:
            self.budget_snapshots.append(context.budget_snapshot)
            return super().resolve(descriptor=descriptor, context=context)

    class _TurnContext:
        requested_write_scope = "disabled"
        requested_write_targets: list[str] = []
        document_context = None

    registry = AssistantToolDescriptorRegistry()
    resolver = _RecordingResolver()
    policy = AssistantToolExposurePolicy(registry=registry, resolver=resolver)
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=AssistantToolExecutor(project_document_capability_service=object()),
        max_iterations=4,
    )

    decisions, visible_descriptors, budget = loop.resolve_policy_bundle(
        turn_context=_TurnContext(),
        project_id=uuid.uuid4(),
    )

    assert budget.max_steps == 4
    assert budget.max_tool_calls == 4
    assert [item.name for item in visible_descriptors] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
    ]
    descriptor_count = len(registry.list_descriptors())
    assert resolver.budget_snapshots.count(None) == descriptor_count
    assert resolver.budget_snapshots.count(budget.model_dump()) == descriptor_count
    assert len(resolver.budget_snapshots) == descriptor_count * 2
    assert decisions[0].descriptor.name == "project.list_documents"


def test_assistant_tool_loop_rejects_budget_dependent_visible_tool_rewrite():
    class _BudgetSensitiveResolver(AssistantToolPolicyResolver):
        def resolve(self, *, descriptor, context) -> AssistantToolPolicyDecision:
            if (
                context.budget_snapshot is not None
                and descriptor.name in {
                    "project.list_documents",
                    "project.search_documents",
                    "project.read_documents",
                }
            ):
                return AssistantToolPolicyDecision(
                    descriptor=descriptor,
                    visibility="hidden",
                    effective_approval_mode=descriptor.approval_mode,
                    hidden_reason="unsupported_approval_mode",
                )
            return super().resolve(descriptor=descriptor, context=context)

    class _TurnContext:
        requested_write_scope = "disabled"
        requested_write_targets: list[str] = []
        document_context = None

    registry = AssistantToolDescriptorRegistry()
    policy = AssistantToolExposurePolicy(
        registry=registry,
        resolver=_BudgetSensitiveResolver(),
    )
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=AssistantToolExecutor(project_document_capability_service=object()),
        max_iterations=4,
    )

    with pytest.raises(
        ConfigurationError,
        match="must not change visible tools after budget_snapshot is applied",
    ):
        loop.resolve_policy_bundle(
            turn_context=_TurnContext(),
            project_id=uuid.uuid4(),
        )


def test_assistant_tool_exposure_policy_only_exposes_project_tools_inside_project_scope():
    registry = AssistantToolDescriptorRegistry()
    policy = AssistantToolExposurePolicy(registry=registry)
    editor_content = "# 人物\n\n林渊"

    assert (
        policy.resolve_visible_tools(
            context=AssistantToolExposureContext(
                project_id=None,
                requested_write_scope="disabled",
            )
        )
        == []
    )
    assert [item.name for item in policy.resolve_visible_tools(
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="disabled",
        )
    )] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents"
    ]
    assert [item.name for item in policy.resolve_visible_tools(
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            allowed_target_document_refs=("project_file:1",),
            active_document_ref="project_file:1",
            active_binding_version="binding-1",
            active_buffer_state={"dirty": False, "base_version": "sha256:base"},
            document_context_bindings=(
                {
                    "document_ref": "project_file:1",
                    "selection_role": "active",
                    "writable": True,
                },
            ),
        )
    )] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
    ]
    assert [item.name for item in policy.resolve_visible_tools(
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            allowed_target_document_refs=("project_file:1",),
            active_document_ref="project_file:1",
            active_binding_version="binding-1",
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version="sha256:base",
                content=editor_content,
            ),
            document_context_bindings=(
                {
                    "document_ref": "project_file:1",
                    "selection_role": "active",
                    "writable": True,
                },
            ),
        )
    )] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents",
        "project.write_document",
    ]
    assert [item.name for item in policy.resolve_visible_tools(
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            allowed_target_document_refs=("project_file:1",),
            active_document_ref="project_file:1",
            active_binding_version="binding-1",
        )
    )] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents"
    ]
    assert [item.name for item in policy.resolve_visible_tools(
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            allowed_target_document_refs=("project_file:1",),
            active_document_ref="project_file:1",
            active_binding_version="binding-1",
            active_buffer_state={"dirty": True, "base_version": "sha256:base"},
        )
    )] == [
        "project.list_documents",
        "project.search_documents",
        "project.read_documents"
    ]


def test_assistant_tool_policy_resolver_reports_hidden_reason_for_missing_project_scope():
    registry = AssistantToolDescriptorRegistry()
    descriptor = registry.get_descriptor("project.read_documents")
    assert descriptor is not None
    resolver = AssistantToolPolicyResolver()

    decision = resolver.resolve(
        descriptor=descriptor,
        context=AssistantToolExposureContext(
            project_id=None,
            requested_write_scope="disabled",
        ),
    )

    assert decision.visibility == "hidden"
    assert decision.hidden_reason == "not_in_project_scope"
    assert decision.effective_approval_mode == "none"


def test_assistant_tool_policy_resolver_keeps_always_confirm_hidden_in_v1a():
    descriptor = AssistantToolDescriptor(
        name="project.always_confirm_document",
        description="需要总是确认的文稿工具。",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        origin="project_document",
        trust_class="local_first_party",
        plane="mutation",
        mutability="write",
        execution_locus="local_runtime",
        approval_mode="always_confirm",
        idempotency_class="conditional_write",
        timeout_seconds=15,
    )
    resolver = AssistantToolPolicyResolver()
    hidden_decision = resolver.resolve(
        descriptor=descriptor,
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            runtime_supports_approval_resume=False,
        ),
    )
    still_hidden_decision = resolver.resolve(
        descriptor=descriptor,
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            runtime_supports_approval_resume=True,
        ),
    )

    assert hidden_decision.visibility == "hidden"
    assert hidden_decision.hidden_reason == "unsupported_approval_mode"
    assert still_hidden_decision.visibility == "hidden"
    assert still_hidden_decision.hidden_reason == "unsupported_approval_mode"


def test_assistant_tool_policy_resolver_builds_approval_grant_for_grant_bound_write():
    registry = AssistantToolDescriptorRegistry()
    descriptor = registry.get_descriptor("project.write_document")
    assert descriptor is not None
    resolver = AssistantToolPolicyResolver()
    document_ref = "project_file:1"
    editor_content = "# 人物\n\n林渊"

    hidden_decision = resolver.resolve(
        descriptor=descriptor,
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
        ),
    )
    visible_decision = resolver.resolve(
        descriptor=descriptor,
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            allowed_target_document_refs=(document_ref,),
            active_document_ref=document_ref,
            active_binding_version="binding-1",
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version="sha256:base",
                content=editor_content,
            ),
            document_context_bindings=(
                {
                    "document_ref": document_ref,
                    "selection_role": "active",
                    "writable": True,
                },
            ),
        ),
    )

    assert hidden_decision.visibility == "hidden"
    assert hidden_decision.hidden_reason == "write_grant_unavailable"
    assert visible_decision.visibility == "visible"
    assert visible_decision.allowed_target_document_refs == (document_ref,)
    assert visible_decision.approval_grant is not None
    assert visible_decision.approval_grant.target_document_refs == (document_ref,)
    assert visible_decision.approval_grant.binding_version_constraints == {
        document_ref: "binding-1"
    }
    assert visible_decision.approval_grant.base_version_constraints == {
        document_ref: "sha256:base"
    }
    assert visible_decision.approval_grant.buffer_hash_constraints == {
        document_ref: build_project_document_buffer_hash(editor_content)
    }
    assert visible_decision.approval_grant.buffer_source_constraints == {
        document_ref: TRUSTED_ACTIVE_BUFFER_SOURCE
    }


def test_assistant_tool_policy_resolver_hides_grant_bound_write_for_non_writable_active_binding():
    registry = AssistantToolDescriptorRegistry()
    descriptor = registry.get_descriptor("project.write_document")
    assert descriptor is not None
    resolver = AssistantToolPolicyResolver()
    document_ref = "canonical:outline"

    decision = resolver.resolve(
        descriptor=descriptor,
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="turn",
            allowed_target_document_refs=(document_ref,),
            active_document_ref=document_ref,
            active_binding_version="binding-1",
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version="sha256:base",
                content="# 大纲\n\n当前大纲",
            ),
            document_context_bindings=(
                {
                    "document_ref": document_ref,
                    "selection_role": "active",
                    "writable": False,
                },
            ),
        ),
    )

    assert decision.visibility == "hidden"
    assert decision.hidden_reason == "write_grant_unavailable"


def test_assistant_tool_loop_rejects_hidden_tool_calls_before_execution():
    class _FailIfExecutedExecutor:
        def __init__(self) -> None:
            self.called = False

        async def execute(self, db, context, *, on_lifecycle_update=None):
            del db, context, on_lifecycle_update
            self.called = True
            raise AssertionError("hidden tool must not be executed")

    registry = AssistantToolDescriptorRegistry()
    read_descriptor = registry.get_descriptor("project.read_documents")
    write_descriptor = registry.get_descriptor("project.write_document")
    assert read_descriptor is not None
    assert write_descriptor is not None
    executor = _FailIfExecutedExecutor()
    loop = AssistantToolLoop(
        exposure_policy=AssistantToolExposurePolicy(registry=registry),
        executor=executor,
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "disabled",
            "requested_write_targets": [],
            "document_context": None,
            "document_context_bindings": [],
        },
    )()

    async def collect():
        return [
            item
            async for item in loop.iterate(
                None,
                turn_context=turn_context,
                owner_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                prompt="先读一下再决定",
                system_prompt="你是小说助手。",
                continuation_support=resolve_continuation_support("openai_responses"),
                model_caller=lambda **_: None,
                initial_raw_output={
                    "content": "",
                    "tool_calls": [
                        {
                            "tool_call_id": "tool-call-write-hidden",
                            "tool_name": "project.write_document",
                            "arguments": {
                                "path": "设定/人物.md",
                                "content": "# 人物\n\n错误写入",
                                "base_version": "sha256:base",
                            },
                        }
                    ],
                },
                tool_policy_decisions=(
                    AssistantToolPolicyDecision(
                        descriptor=read_descriptor,
                        visibility="visible",
                        effective_approval_mode="none",
                    ),
                    AssistantToolPolicyDecision(
                        descriptor=write_descriptor,
                        visibility="hidden",
                        effective_approval_mode="grant_bound",
                        hidden_reason="write_grant_unavailable",
                    ),
                ),
                visible_descriptors=(read_descriptor,),
            )
        ]

    with pytest.raises(AssistantRuntimeTerminalError) as exc_info:
        asyncio.run(collect())

    assert exc_info.value.code == "tool_not_exposed"
    assert str(exc_info.value) == "模型请求了当前 run 未获写入授权的工具：project.write_document。"
    assert executor.called is False


def test_assistant_tool_executor_executes_project_read_documents(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊")
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)

    result = asyncio.run(
        executor.execute(
            async_db(db),
            AssistantToolExecutionContext(
                owner_id=project.owner_id,
                project_id=project.id,
                arguments={"paths": ["设定/人物.md"]},
                run_id=uuid.uuid4(),
                run_audit_id="run-audit-read-1",
                tool_call_id="tool-call-1",
                tool_name="project.read_documents",
                execution_locus="local_runtime",
                requested_write_scope="disabled",
            ),
        )
    )

    assert result.tool_call_id == "tool-call-1"
    assert result.status == "completed"
    assert result.structured_output["documents"][0]["path"] == "设定/人物.md"
    assert result.resource_links[0]["document_ref"].startswith("project_file:")
    assert "林渊" in result.content_items[0]["text"]


def test_assistant_tool_executor_executes_project_list_documents(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊")
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)

    result = asyncio.run(
        executor.execute(
            async_db(db),
            AssistantToolExecutionContext(
                owner_id=project.owner_id,
                project_id=project.id,
                arguments={},
                run_id=uuid.uuid4(),
                run_audit_id="run-audit-list-1",
                tool_call_id="tool-call-list-1",
                tool_name="project.list_documents",
                execution_locus="local_runtime",
                requested_write_scope="disabled",
            ),
        )
    )

    documents = result.structured_output["documents"]
    by_path = {item["path"]: item for item in documents}

    assert result.tool_call_id == "tool-call-list-1"
    assert result.status == "completed"
    assert result.structured_output["catalog_version"].startswith("catalog:")
    assert by_path["大纲/总大纲.md"]["document_ref"] == "canonical:outline"
    assert by_path["设定/人物.md"]["document_ref"].startswith("project_file:")
    assert any("设定/人物.md" in item["text"] for item in result.content_items)


def test_assistant_tool_executor_executes_project_search_documents(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊")
    file_store.save_project_document(
        project.id,
        "数据层/人物关系.json",
        '{\n  "character_relations": []\n}',
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)

    result = asyncio.run(
        executor.execute(
            async_db(db),
            AssistantToolExecutionContext(
                owner_id=project.owner_id,
                project_id=project.id,
                arguments={"query": "人物关系", "limit": 3},
                run_id=uuid.uuid4(),
                run_audit_id="run-audit-search-1",
                tool_call_id="tool-call-search-1",
                tool_name="project.search_documents",
                execution_locus="local_runtime",
                requested_write_scope="disabled",
            ),
        )
    )

    assert result.tool_call_id == "tool-call-search-1"
    assert result.status == "completed"
    assert result.structured_output["catalog_version"].startswith("catalog:")
    assert result.structured_output["documents"][0]["path"] == "数据层/人物关系.json"
    assert result.structured_output["documents"][0]["resource_uri"].startswith("project-document://")
    assert result.resource_links[0]["document_ref"].startswith("project_file:")
    assert result.resource_links[0]["resource_uri"].startswith("project-document://")
    assert "match_score=" in result.content_items[0]["text"]
    assert "matched_fields=" in result.content_items[0]["text"]


def test_assistant_tool_executor_rejects_blank_search_query(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)

    with pytest.raises(ValidationError, match="query 不能为空"):
        asyncio.run(
            executor.execute(
                async_db(db),
                AssistantToolExecutionContext(
                    owner_id=project.owner_id,
                    project_id=project.id,
                    arguments={"query": "   "},
                    run_id=uuid.uuid4(),
                    run_audit_id="run-audit-search-blank",
                    tool_call_id="tool-call-search-blank",
                    tool_name="project.search_documents",
                    execution_locus="local_runtime",
                    requested_write_scope="disabled",
                ),
            )
        )


def test_assistant_tool_executor_rejects_misaligned_read_cursors(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)

    with pytest.raises(ValidationError, match="cursors must align with paths"):
        asyncio.run(
            executor.execute(
                async_db(db),
                AssistantToolExecutionContext(
                    owner_id=project.owner_id,
                    project_id=project.id,
                    arguments={
                        "paths": ["设定/人物.md", "附录/灵感.md"],
                        "cursors": ["offset:0"],
                    },
                    run_id=uuid.uuid4(),
                    run_audit_id="run-audit-read-cursors",
                    tool_call_id="tool-call-read-cursors",
                    tool_name="project.read_documents",
                    execution_locus="local_runtime",
                    requested_write_scope="disabled",
                ),
            )
        )


def test_assistant_tool_executor_includes_read_pagination_and_error_metadata(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    long_text = "# 人物\n\n" + ("林渊\n" * 1500)
    file_store.save_project_document(project.id, "设定/人物.md", long_text)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)

    result = asyncio.run(
        executor.execute(
            async_db(db),
            AssistantToolExecutionContext(
                owner_id=project.owner_id,
                project_id=project.id,
                arguments={"paths": ["设定/人物.md", "设定/不存在.md"]},
                run_id=uuid.uuid4(),
                run_audit_id="run-audit-read-2",
                tool_call_id="tool-call-read-2",
                tool_name="project.read_documents",
                execution_locus="local_runtime",
                requested_write_scope="disabled",
            ),
        )
    )

    assert result.status == "completed"
    assert "truncated=true" in result.content_items[0]["text"]
    assert "next_cursor=offset:" in result.content_items[0]["text"]
    assert any("code=document_not_found" in item["text"] for item in result.content_items[1:])


def test_assistant_tool_loop_returns_errored_envelope_when_read_tool_times_out():
    class _SlowReadExecutor:
        async def execute(self, db, context, *, on_lifecycle_update=None):
            del db, context, on_lifecycle_update
            await asyncio.sleep(1.1)
            return AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={"documents": [], "errors": [], "catalog_version": "catalog"},
            )

    read_descriptor = AssistantToolDescriptor(
        name="project.read_documents",
        description="读取当前项目目录中的一批文稿。",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        origin="project_document",
        trust_class="local_first_party",
        plane="resource",
        mutability="read_only",
        execution_locus="local_runtime",
        approval_mode="none",
        idempotency_class="safe_read",
        timeout_seconds=1,
    )
    registry = AssistantToolDescriptorRegistry(descriptors=(read_descriptor,))
    policy = AssistantToolExposurePolicy(registry=registry)
    step_store = AssistantToolStepStore(Path("/tmp") / f"tool-steps-{uuid.uuid4()}")
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=_SlowReadExecutor(),
        step_store=step_store,
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "disabled",
            "requested_write_targets": [],
            "document_context": None,
        },
    )()

    result = asyncio.run(
        loop._execute_single_tool_call(  # noqa: SLF001
            None,
            step_index=1,
            turn_context=turn_context,
            owner_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            tool_call={
                "tool_call_id": "tool-call-1",
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物.md"]},
            },
            tool_policy_decision=None,
            should_stop=None,
        )
    )

    history = step_store.list_step_history(turn_context.run_id, "tool-call-1")

    assert result.status == "errored"
    assert result.error == {
        "code": "tool_timeout",
        "message": "工具执行超时，已在 1 秒后停止等待。",
        "retryable": False,
        "recovery_hint": "请根据返回错误调整参数或上下文后再试。",
        "requires_user_action": False,
        "recovery_kind": "return_error_to_model",
        "retry_count": 1,
        "timeout_seconds": 1,
    }
    assert [item.status for item in history] == ["reading", "failed"]
    assert history[-1].error_code == "tool_timeout"


def test_assistant_tool_loop_drops_provider_continuation_state_for_runtime_replay():
    class _StaticReadExecutor:
        async def execute(self, db, context, *, on_lifecycle_update=None):
            del db, context, on_lifecycle_update
            return AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={
                    "documents": [{"path": "设定/人物.md"}],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                content_items=[{"type": "text", "text": "设定/人物.md\n\n林渊"}],
            )

    registry = AssistantToolDescriptorRegistry()
    read_descriptor = registry.get_descriptor("project.read_documents")
    assert read_descriptor is not None
    policy = AssistantToolExposurePolicy(registry=registry)
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=_StaticReadExecutor(),
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "disabled",
            "requested_write_targets": [],
            "document_context": None,
        },
    )()
    captured_calls: list[dict[str, object]] = []
    recorded_states: list[object] = []

    async def model_caller(
        *,
        prompt,
        system_prompt,
        tools,
        continuation_items=None,
        provider_continuation_state=None,
    ):
        captured_calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "tools": tools,
                "continuation_items": continuation_items,
                "provider_continuation_state": provider_continuation_state,
            }
        )
        return {
            "content": "后续回复",
            "tool_calls": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
        }

    async def collect():
        return [
            item
            async for item in loop.iterate(
                None,
                turn_context=turn_context,
                owner_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                prompt="先读人物设定",
                system_prompt="你是小说助手。",
                continuation_support=resolve_continuation_support("anthropic_messages"),
                model_caller=model_caller,
                initial_raw_output={
                    "content": "",
                    "tool_calls": [
                        {
                            "tool_call_id": "tool-call-1",
                            "tool_name": "project.read_documents",
                            "arguments": {"paths": ["设定/人物.md"]},
                            "arguments_text": '{"paths":["设定/人物.md"]}',
                            "provider_payload": {
                                "thoughtSignature": "sig_123",
                                "functionCall": {
                                    "id": "fn_123",
                                    "name": "project_read_documents",
                                    "args": {"paths": ["设定/人物.md"]},
                                },
                            },
                        }
                    ],
                    "provider_response_id": "resp_tool_1",
                },
                state_recorder=recorded_states.append,
                visible_descriptors=(read_descriptor,),
            )
        ]

    items = asyncio.run(collect())

    assert captured_calls[0]["provider_continuation_state"] is None
    continuation_items = captured_calls[0]["continuation_items"]
    assert isinstance(continuation_items, list)
    assert [item["item_type"] for item in continuation_items] == ["tool_call", "tool_result"]
    assert recorded_states[-1].continuation_request_snapshot == {
        "continuation_items": continuation_items,
        "provider_continuation_state": None,
    }
    assert items[-1].raw_output is not None
    assert items[-1].raw_output["content"] == "后续回复"


def test_assistant_tool_loop_keeps_provider_continuation_state_for_hybrid_support():
    class _StaticReadExecutor:
        async def execute(self, db, context, *, on_lifecycle_update=None):
            del db, context, on_lifecycle_update
            return AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={
                    "documents": [{"path": "设定/人物.md"}],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                content_items=[{"type": "text", "text": "设定/人物.md\n\n林渊"}],
            )

    registry = AssistantToolDescriptorRegistry()
    read_descriptor = registry.get_descriptor("project.read_documents")
    assert read_descriptor is not None
    policy = AssistantToolExposurePolicy(registry=registry)
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=_StaticReadExecutor(),
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "disabled",
            "requested_write_targets": [],
            "document_context": None,
        },
    )()
    captured_calls: list[dict[str, object]] = []
    recorded_states: list[object] = []

    async def model_caller(
        *,
        prompt,
        system_prompt,
        tools,
        continuation_items=None,
        provider_continuation_state=None,
    ):
        captured_calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "tools": tools,
                "continuation_items": continuation_items,
                "provider_continuation_state": provider_continuation_state,
            }
        )
        return {
            "content": "后续回复",
            "tool_calls": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
        }

    async def collect():
        return [
            item
            async for item in loop.iterate(
                None,
                turn_context=turn_context,
                owner_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                prompt="先读人物设定",
                system_prompt="你是小说助手。",
                continuation_support=resolve_continuation_support("openai_responses"),
                model_caller=model_caller,
                initial_raw_output={
                    "content": "",
                    "tool_calls": [
                        {
                            "tool_call_id": "tool-call-1",
                            "tool_name": "project.read_documents",
                            "arguments": {"paths": ["设定/人物.md"]},
                            "arguments_text": '{"paths":["设定/人物.md"]}',
                            "provider_payload": {
                                "thoughtSignature": "sig_123",
                                "functionCall": {
                                    "id": "fn_123",
                                    "name": "project_read_documents",
                                    "args": {"paths": ["设定/人物.md"]},
                                },
                            },
                        }
                    ],
                    "provider_response_id": "resp_tool_1",
                },
                state_recorder=recorded_states.append,
                visible_descriptors=(read_descriptor,),
            )
        ]

    items = asyncio.run(collect())

    provider_state = captured_calls[0]["provider_continuation_state"]
    assert isinstance(provider_state, dict)
    assert provider_state["previous_response_id"] == "resp_tool_1"
    assert provider_state["latest_items"] == captured_calls[0]["continuation_items"]
    assert captured_calls[0]["continuation_items"][0]["payload"]["provider_payload"] == {
        "thoughtSignature": "sig_123",
        "functionCall": {
            "id": "fn_123",
            "name": "project_read_documents",
            "args": {"paths": ["设定/人物.md"]},
        },
    }
    assert recorded_states[-1].continuation_request_snapshot == {
        "continuation_items": captured_calls[0]["continuation_items"],
        "provider_continuation_state": provider_state,
    }
    assert items[-1].raw_output is not None
    assert items[-1].raw_output["content"] == "后续回复"


def test_build_tool_cycle_continuation_items_preserves_execution_order_and_marks_cycle():
    items = _build_tool_cycle_continuation_items(
        raw_output={"content": "先读取两份人物设定"},
        tool_calls=[
            {
                "tool_call_id": "tool-call-1",
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物-1.md"]},
                "arguments_text": '{"paths":["设定/人物-1.md"]}',
            },
            {
                "tool_call_id": "tool-call-2",
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物-2.md"]},
                "arguments_text": '{"paths":["设定/人物-2.md"]}',
            },
        ],
        tool_results=[
            AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={"documents": [{"path": "设定/人物-1.md"}]},
                content_items=[{"type": "text", "text": "设定/人物-1.md\n\n林渊"}],
            ),
            AssistantToolResultEnvelope(
                tool_call_id="tool-call-2",
                status="completed",
                structured_output={"documents": [{"path": "设定/人物-2.md"}]},
                content_items=[{"type": "text", "text": "设定/人物-2.md\n\n顾砚"}],
            ),
        ],
        tool_cycle_index=3,
    )

    assert [item["item_type"] for item in items] == [
        "message",
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_result",
    ]
    assert [item["call_id"] for item in items[1:]] == [
        "tool-call-1",
        "tool-call-1",
        "tool-call-2",
        "tool-call-2",
    ]
    assert items[1]["tool_cycle_index"] == 3
    assert items[2]["tool_cycle_index"] == 3
    assert items[3]["tool_cycle_index"] == 3
    assert items[4]["tool_cycle_index"] == 3
    assert "tool_cycle_index" not in items[1]["payload"]
    assert "tool_cycle_index" not in items[2]["payload"]


def test_assistant_tool_loop_compacts_runtime_replay_continuation_to_fit_input_budget():
    long_content = "林渊与顾砚的互相试探必须贯穿全文。 " * 120
    initial_raw_output = {
        "content": "",
        "tool_calls": [
            {
                "tool_call_id": "tool-call-1",
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物.md"]},
                "arguments_text": '{"paths":["设定/人物.md"]}',
            }
        ],
    }

    class _StaticReadExecutor:
        async def execute(self, db, context, *, on_lifecycle_update=None):
            del db, context, on_lifecycle_update
            return AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={
                    "documents": [
                        {
                            "path": "设定/人物.md",
                            "document_ref": "project_file:1",
                            "version": "sha256:read-1",
                            "truncated": True,
                            "next_cursor": "offset:4096",
                            "schema_id": "story.character_sheet",
                            "content": long_content,
                            "resource_uri": "resource://project/1/%E8%AE%BE%E5%AE%9A/%E4%BA%BA%E7%89%A9.md",
                            "binding_version": "binding-1",
                            "title": "人物",
                            "source": "project_file",
                            "document_kind": "story_note",
                            "mime_type": "text/markdown",
                            "content_state": "ready",
                            "writable": True,
                        }
                    ],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                content_items=[
                    {
                        "type": "text",
                        "text": "设定/人物.md\ndocument_ref=project_file:1\nversion=sha256:read-1\ntruncated=true\nnext_cursor=offset:4096\n\n"
                        + long_content,
                    }
                ],
            )

    registry = AssistantToolDescriptorRegistry()
    read_descriptor = registry.get_descriptor("project.read_documents")
    assert read_descriptor is not None
    policy = AssistantToolExposurePolicy(registry=registry)
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=_StaticReadExecutor(),
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "disabled",
            "requested_write_targets": [],
            "document_context": None,
        },
    )()
    captured_calls: list[dict[str, object]] = []
    recorded_states: list[object] = []

    async def model_caller(
        *,
        prompt,
        system_prompt,
        tools,
        continuation_items=None,
        provider_continuation_state=None,
    ):
        captured_calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "tools": tools,
                "continuation_items": continuation_items,
                "provider_continuation_state": provider_continuation_state,
            }
        )
        return {
            "content": "后续回复",
            "tool_calls": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
        }

    async def collect():
        return [
            item
            async for item in loop.iterate(
                None,
                turn_context=turn_context,
                owner_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                prompt="先读人物设定",
                system_prompt="你是小说助手。",
                continuation_support=resolve_continuation_support("anthropic_messages"),
                model_caller=model_caller,
                initial_raw_output=initial_raw_output,
                    run_budget=AssistantRunBudget(
                        max_steps=8,
                        max_tool_calls=8,
                        max_input_tokens=900,
                        max_parallel_tool_calls=1,
                        tool_timeout_seconds=15,
                    ),
                state_recorder=recorded_states.append,
                visible_descriptors=(read_descriptor,),
            )
        ]

    asyncio.run(collect())

    continuation_items = captured_calls[0]["continuation_items"]
    assert isinstance(continuation_items, list)
    tool_result = continuation_items[1]
    payload = tool_result["payload"]
    document = payload["structured_output"]["documents"][0]
    assert document["truncated"] is True
    assert document["next_cursor"] == "offset:4096"
    assert "resource_uri" not in document
    assert len(document["content"]) < len(long_content)
    assert len(payload["content_items"][0]["text"]) < len(long_content)
    assert recorded_states
    assert recorded_states[-1].continuation_request_snapshot == {
        "continuation_items": continuation_items,
        "provider_continuation_state": None,
    }
    snapshot = recorded_states[-1].continuation_compaction_snapshot
    assert snapshot is not None
    assert snapshot["phase"] == "tool_loop_continuation"
    assert snapshot["level"] == "soft"
    assert snapshot["estimated_tokens_before"] > snapshot["estimated_tokens_after"]
    assert snapshot["compacted_item_count"] >= 1
    assert snapshot["compacted_tool_names"] == ["project.read_documents"]
    assert snapshot["compacted_document_refs"] == ["project_file:1"]
    assert snapshot["compacted_document_versions"] == {"project_file:1": "sha256:read-1"}
    assert snapshot["compacted_catalog_versions"] == ["catalog-v1"]
    original_tool_result_item = _build_tool_cycle_continuation_items(
        raw_output=initial_raw_output,
        tool_calls=initial_raw_output["tool_calls"],
        tool_results=[
            AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={
                    "documents": [
                        {
                            "path": "设定/人物.md",
                            "document_ref": "project_file:1",
                            "version": "sha256:read-1",
                            "truncated": True,
                            "next_cursor": "offset:4096",
                            "schema_id": "story.character_sheet",
                            "content": long_content,
                            "resource_uri": "resource://project/1/%E8%AE%BE%E5%AE%9A/%E4%BA%BA%E7%89%A9.md",
                            "binding_version": "binding-1",
                            "title": "人物",
                            "source": "project_file",
                            "document_kind": "story_note",
                            "mime_type": "text/markdown",
                            "content_state": "ready",
                            "writable": True,
                        }
                    ],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                content_items=[
                    {
                        "type": "text",
                        "text": "设定/人物.md\ndocument_ref=project_file:1\nversion=sha256:read-1\n"
                        "truncated=true\nnext_cursor=offset:4096\n\n" + long_content,
                    }
                ],
            )
        ],
        tool_cycle_index=0,
    )[1]
    assert snapshot["compressed_items_digest"] == build_structured_items_digest(
        [original_tool_result_item]
    )
    assert snapshot["projected_items_digest"] == build_structured_items_digest(
        continuation_items
    )
    assert snapshot["compressed_items_digest"] != snapshot["projected_items_digest"]


def test_apply_tool_loop_request_budget_drops_oldest_tool_cycle_when_gemini_provider_metadata_exceeds_budget():
    continuation_items = (
        {
            "item_type": "message",
            "role": "assistant",
            "content": "我先读第一份设定。",
        },
        {
            "item_type": "tool_call",
            "call_id": "tool-call-1",
            "tool_cycle_index": 0,
            "payload": {
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物-1.md"]},
                "arguments_text": '{"paths":["设定/人物-1.md"]}',
                "provider_payload": {
                    "thoughtSignature": "sig_old_" + ("x" * 4000),
                    "functionCall": {
                        "id": "fn_1",
                        "name": "project_read_documents",
                        "args": {"paths": ["设定/人物-1.md"]},
                    },
                },
            },
        },
        {
            "item_type": "tool_result",
            "call_id": "tool-call-1",
            "tool_name": "project.read_documents",
            "status": "completed",
            "tool_cycle_index": 0,
            "payload": {
                "structured_output": {
                    "documents": [{"path": "设定/人物-1.md"}],
                    "errors": [],
                },
                "content_items": [{"type": "text", "text": "设定/人物-1.md\n\n林渊"}],
                "resource_links": [],
                "error": None,
            },
        },
        {
            "item_type": "message",
            "role": "assistant",
            "content": "再读第二份设定。",
        },
        {
            "item_type": "tool_call",
            "call_id": "tool-call-2",
            "tool_cycle_index": 1,
            "payload": {
                "tool_name": "project.read_documents",
                "arguments": {"paths": ["设定/人物-2.md"]},
                "arguments_text": '{"paths":["设定/人物-2.md"]}',
                "provider_payload": {
                    "thoughtSignature": "sig_new",
                    "functionCall": {
                        "id": "fn_2",
                        "name": "project_read_documents",
                        "args": {"paths": ["设定/人物-2.md"]},
                    },
                },
            },
        },
        {
            "item_type": "tool_result",
            "call_id": "tool-call-2",
            "tool_name": "project.read_documents",
            "status": "completed",
            "tool_cycle_index": 1,
            "payload": {
                "structured_output": {
                    "documents": [{"path": "设定/人物-2.md"}],
                    "errors": [],
                },
                "content_items": [{"type": "text", "text": "设定/人物-2.md\n\n顾砚"}],
                "resource_links": [],
                "error": None,
            },
        },
    )

    compacted_items, _, snapshot = apply_tool_loop_request_budget(
        prompt="继续。",
        system_prompt="你是小说助手。",
        tool_schemas=[],
        continuation_items=continuation_items,
        provider_continuation_state=None,
        continuation_support=resolve_continuation_support("gemini_generate_content"),
        run_budget=AssistantRunBudget(
            max_steps=8,
            max_tool_calls=8,
            max_input_tokens=500,
            max_parallel_tool_calls=1,
            tool_timeout_seconds=15,
        ),
    )

    assert [item["item_type"] for item in compacted_items] == [
        "message",
        "tool_call",
        "tool_result",
    ]
    assert compacted_items[0]["role"] == "assistant"
    assert isinstance(compacted_items[0]["content"], str)
    assert compacted_items[0]["content"].strip()
    assert compacted_items[1]["call_id"] == "tool-call-2"
    assert compacted_items[2]["call_id"] == "tool-call-2"
    assert snapshot is not None
    assert snapshot["level"] == "hard"
    assert snapshot["compacted_item_count"] == 5
    assert snapshot["retained_item_count"] == 3
    assert snapshot["trimmed_text_slot_count"] == 1
    assert snapshot["dropped_content_item_count"] == 1
    assert snapshot["compacted_tool_names"] == ["project.read_documents"]
    assert snapshot["compacted_document_refs"] == []
    assert snapshot["compacted_document_versions"] == {}
    assert snapshot["compacted_catalog_versions"] == []
    assert snapshot["compressed_items_digest"] == build_structured_items_digest(
        [
            continuation_items[0],
            continuation_items[1],
            continuation_items[2],
            continuation_items[3],
            continuation_items[5],
        ]
    )
    assert snapshot["projected_items_digest"] == build_structured_items_digest(
        compacted_items
    )


def test_assistant_tool_loop_preserves_provider_final_output_items():
    class _StaticReadExecutor:
        async def execute(self, db, context, *, on_lifecycle_update=None):
            del db, context, on_lifecycle_update
            return AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={
                    "documents": [{"path": "设定/人物.md"}],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                content_items=[{"type": "text", "text": "设定/人物.md\n\n林渊"}],
            )

    registry = AssistantToolDescriptorRegistry()
    read_descriptor = registry.get_descriptor("project.read_documents")
    assert read_descriptor is not None
    policy = AssistantToolExposurePolicy(registry=registry)
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=_StaticReadExecutor(),
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "disabled",
            "requested_write_targets": [],
            "document_context": None,
        },
    )()

    async def model_caller(
        *,
        prompt,
        system_prompt,
        tools,
        continuation_items=None,
        provider_continuation_state=None,
    ):
        del prompt, system_prompt, tools, continuation_items, provider_continuation_state
        return {
            "content": "我暂时不能直接给出最终方案。",
            "tool_calls": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
            "output_items": [
                {
                    "item_type": "reasoning",
                    "item_id": "provider:openai_responses:reasoning:1",
                    "status": "completed",
                    "provider_ref": "rs_1",
                    "payload": {"type": "reasoning", "summary": "检查读取结果"},
                },
                {
                    "item_type": "refusal",
                    "item_id": "provider:openai_responses:refusal:1",
                    "status": "completed",
                    "provider_ref": "rs_2",
                    "payload": {"type": "refusal", "reason": "insufficient_context"},
                },
                {
                    "item_type": "text",
                    "item_id": "provider:openai_responses:text:1",
                    "status": "completed",
                    "provider_ref": "rs_3",
                    "payload": {"content": "我暂时不能直接给出最终方案。", "phase": "final"},
                },
            ],
        }

    async def collect():
        return [
            item
            async for item in loop.iterate(
                None,
                turn_context=turn_context,
                owner_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                prompt="先读人物设定",
                system_prompt="你是小说助手。",
                continuation_support=resolve_continuation_support("openai_responses"),
                model_caller=model_caller,
                initial_raw_output={
                    "content": "",
                    "tool_calls": [
                        {
                            "tool_call_id": "tool-call-1",
                            "tool_name": "project.read_documents",
                            "arguments": {"paths": ["设定/人物.md"]},
                            "arguments_text": '{"paths":["设定/人物.md"]}',
                        }
                    ],
                    "provider_response_id": "resp_tool_1",
                },
                visible_descriptors=(read_descriptor,),
            )
        ]

    items = asyncio.run(collect())

    assert items[-1].raw_output is not None
    assert [item["item_type"] for item in items[-1].raw_output["output_items"]] == [
        "tool_call",
        "tool_result",
        "reasoning",
        "refusal",
        "text",
    ]
    assert items[-1].raw_output["output_items"][-1]["item_id"] == "provider:openai_responses:text:1"
    assert not any(
        item["item_id"] == f"{turn_context.run_id}:text:2"
        for item in items[-1].raw_output["output_items"]
    )


def test_apply_tool_loop_request_budget_raises_shared_budget_exhausted_when_prompt_alone_exceeds_budget():
    huge_prompt = "人物关系、势力关系和贯穿全文的主线都不能丢。 " * 80
    continuation_items = (
        {
            "item_type": "message",
            "role": "assistant",
            "content": "我先读取人物设定。",
        },
        {
            "item_type": "tool_result",
            "status": "completed",
            "call_id": "tool-call-1",
            "tool_name": "project.read_documents",
            "payload": {
                "tool_name": "project.read_documents",
                "structured_output": {
                    "documents": [],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                "content_items": [{"type": "text", "text": "设定/人物.md"}],
                "resource_links": [],
                "error": None,
            },
        },
    )

    with pytest.raises(AssistantRuntimeTerminalError) as exc_info:
        apply_tool_loop_request_budget(
            prompt=huge_prompt,
            system_prompt="你是小说助手。",
            tool_schemas=[{"type": "function", "function": {"name": "project.read_documents"}}],
            continuation_items=continuation_items,
            provider_continuation_state=None,
            continuation_support=resolve_continuation_support("anthropic_messages"),
            run_budget=AssistantRunBudget(
                max_steps=8,
                max_tool_calls=8,
                max_input_tokens=32,
                max_parallel_tool_calls=1,
                tool_timeout_seconds=15,
            ),
        )

    assert exc_info.value.code == "budget_exhausted"
    assert str(exc_info.value) == "本轮上下文预算已耗尽，压缩后仍无法继续执行。"


def test_assistant_tool_loop_emits_streamed_continuation_chunks():
    class _StaticReadExecutor:
        async def execute(self, db, context, *, on_lifecycle_update=None):
            del db, context, on_lifecycle_update
            return AssistantToolResultEnvelope(
                tool_call_id="tool-call-1",
                status="completed",
                structured_output={
                    "documents": [{"path": "设定/人物.md"}],
                    "errors": [],
                    "catalog_version": "catalog-v1",
                },
                content_items=[{"type": "text", "text": "设定/人物.md\n\n林渊"}],
            )

    registry = AssistantToolDescriptorRegistry()
    read_descriptor = registry.get_descriptor("project.read_documents")
    assert read_descriptor is not None
    policy = AssistantToolExposurePolicy(registry=registry)
    loop = AssistantToolLoop(
        exposure_policy=policy,
        executor=_StaticReadExecutor(),
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "disabled",
            "requested_write_targets": [],
            "document_context": None,
        },
    )()

    async def model_caller(
        *,
        prompt,
        system_prompt,
        tools,
        continuation_items=None,
        provider_continuation_state=None,
    ):
        del prompt, system_prompt, tools, continuation_items, provider_continuation_state
        raise AssertionError("streamed continuation path should not call non-stream model_caller")

    async def stream_model_caller(
        *,
        prompt,
        system_prompt,
        tools,
        continuation_items=None,
        provider_continuation_state=None,
    ):
        del prompt, system_prompt, tools, continuation_items, provider_continuation_state
        yield AssistantToolLoopModelStreamEvent(delta="后续")
        yield AssistantToolLoopModelStreamEvent(delta="回复")
        yield AssistantToolLoopModelStreamEvent(
            raw_output={
                "content": "后续回复",
                "tool_calls": [],
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
            }
        )

    async def collect():
        return [
            item
            async for item in loop.iterate(
                None,
                turn_context=turn_context,
                owner_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                prompt="先读人物设定",
                system_prompt="你是小说助手。",
                continuation_support=resolve_continuation_support("openai_responses"),
                model_caller=model_caller,
                stream_model_caller=stream_model_caller,
                initial_raw_output={
                    "content": "",
                    "tool_calls": [
                        {
                            "tool_call_id": "tool-call-1",
                            "tool_name": "project.read_documents",
                            "arguments": {"paths": ["设定/人物.md"]},
                            "arguments_text": '{"paths":["设定/人物.md"]}',
                        }
                    ],
                    "provider_response_id": "resp_tool_1",
                },
                visible_descriptors=(read_descriptor,),
            )
        ]

    items = asyncio.run(collect())

    assert [item.event_name for item in items[:-1]] == ["tool_call_start", "tool_call_result", "chunk", "chunk"]
    assert [item.event_payload["delta"] for item in items[2:4]] == ["后续", "回复"]
    assert items[-1].raw_output is not None
    assert items[-1].raw_output["content"] == "后续回复"
    assert items[-1].raw_output_already_streamed is True


def test_assistant_tool_executor_executes_project_write_document(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    run_id = uuid.uuid4()
    run_audit_id = f"{run_id}:tool-call-write-1"
    binding_version = _build_binding_version(
        target.path,
        target.document_ref,
        source=target.source,
        document_kind=target.document_kind,
        writable=target.writable,
    )

    result = asyncio.run(
        executor.execute(
            async_db(db),
            AssistantToolExecutionContext(
                owner_id=project.owner_id,
                project_id=project.id,
                arguments={
                    "path": "设定/人物.md",
                    "content": "# 人物\n\n林渊\n\n新增：对雨夜异常高度敏感。",
                    "base_version": target.version,
                },
                run_id=run_id,
                run_audit_id=run_audit_id,
                tool_call_id="tool-call-write-1",
                tool_name="project.write_document",
                execution_locus="local_runtime",
                requested_write_scope="turn",
                allowed_target_document_refs=(target.document_ref,),
                approval_grant=_build_turn_approval_grant(
                    tool_name="project.write_document",
                    document_ref=target.document_ref,
                    binding_version=binding_version,
                    base_version=target.version,
                    buffer_hash=build_project_document_buffer_hash(current_content),
                    buffer_source=TRUSTED_ACTIVE_BUFFER_SOURCE,
                ),
                active_document_ref=target.document_ref,
                active_binding_version=binding_version,
                active_buffer_state=_build_trusted_active_buffer_state(
                    base_version=target.version,
                    content=current_content,
                ),
            ),
        )
    )

    assert result.status == "completed"
    assert result.structured_output["path"] == "设定/人物.md"
    assert result.structured_output["document_ref"] == target.document_ref
    assert result.structured_output["run_audit_id"] == run_audit_id
    assert result.audit == {"run_audit_id": run_audit_id}


def test_build_tool_call_start_payload_includes_write_and_search_target_summary() -> None:
    write_payload = _build_tool_call_start_payload(
        {
            "tool_call_id": "tool-call-write-1",
            "tool_name": "project.write_document",
            "arguments": {
                "path": "设定/人物.md",
                "base_version": "sha256:base",
            },
        }
    )
    search_payload = _build_tool_call_start_payload(
        {
            "tool_call_id": "tool-call-search-1",
            "tool_name": "project.search_documents",
            "arguments": {
                "query": "人物关系",
                "path_prefix": "数据层",
                "sources": ["file"],
                "schema_ids": ["project.character_relations"],
                "content_states": ["ready"],
                "limit": 5,
            },
        }
    )

    assert write_payload["target_summary"] == {
        "path": "设定/人物.md",
        "base_version": "sha256:base",
    }
    assert "arguments" not in write_payload
    assert "arguments_text" not in write_payload
    assert search_payload["target_summary"] == {
        "path_prefix": "数据层",
        "query": "人物关系",
        "limit": 5,
        "sources": ["file"],
        "schema_ids": ["project.character_relations"],
        "content_states": ["ready"],
    }
    assert "arguments" not in search_payload
    assert "arguments_text" not in search_payload


def test_assistant_tool_executor_raises_terminal_error_for_unauthorized_write_target(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    binding_version = _build_binding_version(
        target.path,
        target.document_ref,
        source=target.source,
        document_kind=target.document_kind,
        writable=target.writable,
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        asyncio.run(
            executor.execute(
                async_db(db),
                AssistantToolExecutionContext(
                    owner_id=project.owner_id,
                    project_id=project.id,
                    arguments={
                        "path": "设定/人物.md",
                        "content": "# 人物\n\n林渊\n\n新增设定。",
                        "base_version": target.version,
                    },
                    run_id=uuid.uuid4(),
                    run_audit_id="run-audit-write-2",
                    tool_call_id="tool-call-write-2",
                    tool_name="project.write_document",
                    execution_locus="local_runtime",
                    requested_write_scope="disabled",
                    allowed_target_document_refs=(target.document_ref,),
                    active_document_ref=target.document_ref,
                    active_binding_version=binding_version,
                    active_buffer_state=_build_trusted_active_buffer_state(
                        base_version=target.version,
                        content=current_content,
                    ),
                ),
            )
        )

    assert exc_info.value.code == "write_not_authorized"
    assert str(exc_info.value) == "当前 turn 没有启用文稿写回能力。"


def test_assistant_tool_loop_returns_errored_envelope_for_recoverable_write_conflict(
    db,
    tmp_path,
):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")
    registry = AssistantToolDescriptorRegistry()
    write_descriptor = registry.get_descriptor("project.write_document")
    assert write_descriptor is not None
    step_store = AssistantToolStepStore(Path("/tmp") / f"tool-steps-{uuid.uuid4()}")
    loop = AssistantToolLoop(
        exposure_policy=AssistantToolExposurePolicy(registry=registry),
        executor=AssistantToolExecutor(project_document_capability_service=capability_service),
        step_store=step_store,
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "turn",
            "requested_write_targets": [target.document_ref],
            "document_context": {
                "active_document_ref": target.document_ref,
                "active_binding_version": _build_binding_version(
                    target.path,
                    target.document_ref,
                    source=target.source,
                    document_kind=target.document_kind,
                    writable=target.writable,
                ),
                "active_buffer_state": _build_trusted_active_buffer_state(
                    base_version="sha256:stale",
                    content=current_content,
                ),
            },
            "document_context_bindings": [],
        },
    )()

    result = asyncio.run(
        loop._execute_single_tool_call(  # noqa: SLF001
            async_db(db),
            step_index=1,
            turn_context=turn_context,
            owner_id=project.owner_id,
            project_id=project.id,
            tool_call={
                "tool_call_id": "tool-call-write-conflict",
                "tool_name": "project.write_document",
                "arguments": {
                    "path": "设定/人物.md",
                    "content": "# 人物\n\n错误覆盖",
                    "base_version": "sha256:stale",
                },
            },
            descriptor=write_descriptor,
            tool_policy_decision=AssistantToolPolicyDecision(
                descriptor=write_descriptor,
                visibility="visible",
                effective_approval_mode="grant_bound",
                allowed_target_document_refs=(target.document_ref,),
                approval_grant=_build_turn_approval_grant(
                    tool_name="project.write_document",
                    document_ref=target.document_ref,
                    binding_version=turn_context.document_context["active_binding_version"],
                    base_version="sha256:stale",
                    buffer_hash=build_project_document_buffer_hash(current_content),
                    buffer_source=TRUSTED_ACTIVE_BUFFER_SOURCE,
                ),
            ),
            should_stop=None,
        )
    )

    history = step_store.list_step_history(turn_context.run_id, "tool-call-write-conflict")

    assert result.status == "errored"
    assert result.error == {
        "code": "version_conflict",
        "message": "目标文稿版本已变化，请重新读取最新内容后再写入。",
        "retryable": False,
        "recovery_hint": "请先重新读取目标文稿的最新状态，再决定是否继续写入。",
        "requires_user_action": True,
        "recovery_kind": "return_error_to_model",
    }
    assert [item.status for item in history] == ["validating", "failed"]
    assert history[-1].error_code == "version_conflict"
    assert history[-1].approval_grant_id is not None
    assert history[-1].approval_grant_snapshot == {
        "grant_id": history[-1].approval_grant_id,
        "allowed_tool_names": ["project.write_document"],
        "target_document_refs": [target.document_ref],
        "binding_version_constraints": {
            target.document_ref: turn_context.document_context["active_binding_version"]
        },
        "base_version_constraints": {
            target.document_ref: "sha256:stale"
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


def test_assistant_tool_loop_marks_grant_bound_write_pending_without_approval_grant(
    db,
    tmp_path,
):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")
    registry = AssistantToolDescriptorRegistry()
    write_descriptor = registry.get_descriptor("project.write_document")
    assert write_descriptor is not None
    step_store = AssistantToolStepStore(Path("/tmp") / f"tool-steps-{uuid.uuid4()}")
    loop = AssistantToolLoop(
        exposure_policy=AssistantToolExposurePolicy(registry=registry),
        executor=AssistantToolExecutor(project_document_capability_service=capability_service),
        step_store=step_store,
    )
    binding_version = _build_binding_version(
        target.path,
        target.document_ref,
        source=target.source,
        document_kind=target.document_kind,
        writable=target.writable,
    )
    turn_context = type(
        "_TurnContext",
        (),
        {
            "run_id": uuid.uuid4(),
            "requested_write_scope": "turn",
            "requested_write_targets": [target.document_ref],
            "document_context": {
                "active_document_ref": target.document_ref,
                "active_binding_version": binding_version,
                "active_buffer_state": _build_trusted_active_buffer_state(
                    base_version=target.version,
                    content=current_content,
                ),
            },
            "document_context_bindings": [],
        },
    )()

    with pytest.raises(BusinessRuleError) as exc_info:
        asyncio.run(
            loop._execute_single_tool_call(  # noqa: SLF001
                async_db(db),
                step_index=1,
                turn_context=turn_context,
                owner_id=project.owner_id,
                project_id=project.id,
                tool_call={
                    "tool_call_id": "tool-call-write-no-grant",
                    "tool_name": "project.write_document",
                    "arguments": {
                        "path": "设定/人物.md",
                        "content": "# 人物\n\n林渊\n\n新增设定。",
                        "base_version": target.version,
                    },
                },
                descriptor=write_descriptor,
                tool_policy_decision=AssistantToolPolicyDecision(
                    descriptor=write_descriptor,
                    visibility="visible",
                    effective_approval_mode="grant_bound",
                    allowed_target_document_refs=(target.document_ref,),
                ),
                should_stop=None,
            )
        )

    history = step_store.list_step_history(turn_context.run_id, "tool-call-write-no-grant")

    assert exc_info.value.code == "write_grant_expired"
    assert [item.status for item in history] == ["validating", "failed"]
    assert history[0].approval_state == "pending"
    assert history[-1].approval_state == "pending"
    assert history[-1].error_code == "write_grant_expired"


def _build_binding_version(
    path: str,
    document_ref: str,
    *,
    source: str,
    document_kind: str,
    writable: bool,
) -> str:
    payload = json.dumps(
        {
            "document_ref": document_ref,
            "document_kind": document_kind,
            "path": path,
            "source": source,
            "writable": writable,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_turn_approval_grant(
    *,
    tool_name: str,
    document_ref: str,
    binding_version: str,
    base_version: str,
    buffer_hash: str = "fnv1a64:test",
    buffer_source: str = TRUSTED_ACTIVE_BUFFER_SOURCE,
) -> AssistantToolApprovalGrant:
    return AssistantToolApprovalGrant(
        grant_id=f"grant:test:{tool_name}:{document_ref}",
        allowed_tool_names=(tool_name,),
        target_document_refs=(document_ref,),
        binding_version_constraints={document_ref: binding_version},
        base_version_constraints={document_ref: base_version},
        approval_mode_snapshot="grant_bound",
        buffer_hash_constraints={document_ref: buffer_hash},
        buffer_source_constraints={document_ref: buffer_source},
        expires_at=None,
    )
