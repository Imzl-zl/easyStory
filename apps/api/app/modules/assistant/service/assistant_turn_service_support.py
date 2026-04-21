from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import HookConfig
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse

from .assistant_execution_support import require_text_output
from .assistant_runtime_claim_support import resolve_runtime_claim_state
from .assistant_runtime_terminal import attach_assistant_stream_error_meta
from .assistant_runtime_terminal import AssistantRuntimeTerminalError
from .turn.assistant_turn_execution_runtime import AssistantTurnExecutionRuntime
from .dto import (
    AssistantHookResultDTO,
    AssistantTurnRequestDTO,
    AssistantTurnResponseDTO,
)
from .turn.assistant_turn_finalize_runtime import AssistantTurnFinalizeRuntime
from .turn.assistant_turn_prepare_runtime import (
    AssistantTurnPrepareRuntimeResult,
    AssistantTurnPrepareRuntime,
)
from .turn.assistant_turn_prepare_support import prepare_assistant_turn, resolve_requested_hooks
from .turn.assistant_turn_recovery_runtime import AssistantTurnRecoveryRuntime
from .turn.assistant_turn_run_support import (
    build_running_turn_record,
    build_terminal_turn_record,
    ensure_existing_turn_matches_request,
    recover_existing_turn,
)
from .turn.assistant_turn_runtime_support import (
    PreparedAssistantTurn,
    build_after_assistant_payload,
    build_turn_response,
)
from .turn.assistant_turn_terminal_persist_runtime import AssistantTurnTerminalPersistRuntime
from .turn.assistant_turn_stream_execution_runtime import (
    AssistantTurnStreamExecutionRuntime,
)
from .turn.assistant_turn_llm_bridge_support import should_stream_with_tool_loop

if TYPE_CHECKING:
    from .assistant_llm_runtime_support import AssistantLlmTransportMode
    from .assistant_service import AssistantService


async def prepare_turn(
    service: "AssistantService",
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    transport_mode: "AssistantLlmTransportMode" = "buffered",
    resolved_hooks: list[HookConfig] | None = None,
) -> PreparedAssistantTurn:
    return await prepare_assistant_turn(
        db,
        payload,
        owner_id=owner_id,
        transport_mode=transport_mode,
        resolved_hooks=resolved_hooks,
        config_loader=service.config_loader,
        template_renderer=service.template_renderer,
        project_service=service.project_service,
        assistant_preferences_service=service.assistant_preferences_service,
        assistant_rule_service=service.assistant_rule_service,
        assistant_agent_service=service.assistant_agent_service,
        assistant_skill_service=service.assistant_skill_service,
        assistant_hook_service=service.assistant_hook_service,
        assistant_tool_loop=service.assistant_tool_loop,
        turn_run_store=service.turn_run_store,
        project_document_capability_service=service.project_document_capability_service,
        resolve_llm_runtime=service._resolve_llm_runtime,
    )


async def execute_turn(
    service: "AssistantService",
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
) -> AssistantTurnResponseDTO:
    turn_start = await prepare_or_recover_turn(
        service,
        db,
        payload,
        owner_id=owner_id,
        transport_mode="buffered",
    )
    prepared = turn_start.prepared
    replayed_response = turn_start.replayed_response
    if replayed_response is not None:
        return replayed_response
    runtime = AssistantTurnExecutionRuntime(
        run_before_hooks=lambda: run_before_turn_hooks(
            service,
            db,
            prepared,
            owner_id=owner_id,
        ),
        call_turn_llm=lambda: service._call_turn_llm(
            db,
            prepared.hooks,
            prompt=prepared.prompt,
            before_payload=prepared.before_payload,
            owner_id=owner_id,
            project_id=prepared.project_id,
            spec=prepared.spec,
            system_prompt=prepared.system_prompt,
            turn_context=prepared.turn_context,
            run_budget=prepared.run_budget,
            tool_policy_decisions=prepared.tool_policy_decisions,
            visible_tool_descriptors=prepared.visible_tool_descriptors,
            runtime_context=prepared.resolved_llm_runtime,
        ),
        finalize_response=lambda before_results, raw_output: finalize_turn(
            service,
            db,
            payload,
            prepared,
            raw_output,
            before_results=before_results,
            owner_id=owner_id,
        ),
        run_prepared_on_error_hooks=lambda error: run_prepared_on_error_hooks(
            service,
            db,
            prepared,
            error=error,
            owner_id=owner_id,
        ),
        store_terminal_turn=lambda **kwargs: store_terminal_turn(
            service,
            prepared,
            owner_id=owner_id,
            **kwargs,
        ),
    )
    return await runtime.run()


async def iterate_stream_turn(
    service: "AssistantService",
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    should_stop: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    turn_start = await prepare_or_recover_turn(
        service,
        db,
        payload,
        owner_id=owner_id,
        transport_mode="stream",
    )
    prepared = turn_start.prepared
    replayed_response = turn_start.replayed_response
    runtime = AssistantTurnStreamExecutionRuntime(
        replayed_response=replayed_response,
        build_stream_event_data=lambda event_seq, extra=None: build_stream_event_data(
            service,
            prepared,
            event_seq=event_seq,
            extra=extra,
        ),
        run_started_extra={
            "requested_write_scope": prepared.turn_context.requested_write_scope,
            "requested_write_targets": prepared.turn_context.requested_write_targets,
        },
        run_before_hooks=lambda: run_before_turn_hooks(
            service,
            db,
            prepared,
            owner_id=owner_id,
        ),
        should_stream_with_tool_loop=should_stream_with_tool_loop(
            assistant_tool_loop=service.assistant_tool_loop,
            prepared=prepared,
        ),
        stream_tool_loop=lambda: service._stream_turn_with_tool_loop(
            db,
            prepared,
            owner_id=owner_id,
            should_stop=should_stop,
        ),
        call_turn_llm_stream=lambda: service._call_turn_llm_stream(
            db,
            prepared.hooks,
            prompt=prepared.prompt,
            before_payload=prepared.before_payload,
            owner_id=owner_id,
            project_id=prepared.project_id,
            spec=prepared.spec,
            system_prompt=prepared.system_prompt,
            runtime_context=prepared.resolved_llm_runtime,
            should_stop=should_stop,
        ),
        finalize_response=lambda before_results, raw_output: finalize_turn(
            service,
            db,
            payload,
            prepared,
            raw_output,
            before_results=before_results,
            owner_id=owner_id,
        ),
        run_prepared_on_error_hooks=lambda error: run_prepared_on_error_hooks(
            service,
            db,
            prepared,
            error=error,
            owner_id=owner_id,
        ),
        store_terminal_turn=lambda **kwargs: store_terminal_turn(
            service,
            prepared,
            owner_id=owner_id,
            **kwargs,
        ),
        attach_stream_error_meta=attach_assistant_stream_error_meta,
    )
    async for event_name, event_data in runtime.iterate():
        yield event_name, event_data


async def prepare_or_recover_turn(
    service: "AssistantService",
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    transport_mode: "AssistantLlmTransportMode" = "buffered",
) -> AssistantTurnPrepareRuntimeResult:
    runtime = AssistantTurnPrepareRuntime(
        resolve_hooks=lambda: resolve_requested_hooks(
            assistant_hook_service=service.assistant_hook_service,
            hook_ids=payload.hook_ids,
            owner_id=owner_id,
        ),
        prepare_turn=lambda resolved_hooks: service._prepare_turn(
            db,
            payload,
            owner_id=owner_id,
            transport_mode=transport_mode,
            resolved_hooks=resolved_hooks,
        ),
        run_prepare_on_error_hooks=lambda resolved_hooks, error: run_prepare_on_error_hooks(
            service,
            db,
            payload,
            hooks=resolved_hooks,
            error=error,
            owner_id=owner_id,
        ),
        recover_or_start_turn=lambda prepared: recover_or_start_turn(
            service,
            prepared,
            owner_id=owner_id,
        ),
    )
    return await runtime.run()


async def recover_or_start_turn(
    service: "AssistantService",
    prepared: PreparedAssistantTurn,
    *,
    owner_id: uuid.UUID,
) -> AssistantTurnResponseDTO | None:
    if service.turn_run_store is None:
        return None
    runtime = AssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: asyncio.to_thread(
            service.turn_run_store.get_run,
            prepared.turn_context.run_id,
        ),
        recover_existing_running_turn=lambda existing_run: recover_existing_running_turn(
            service,
            prepared,
            existing_run=existing_run,
            owner_id=owner_id,
        ),
        recover_existing_turn=lambda existing_run: recover_existing_turn(
            prepared=prepared,
            existing_run=existing_run,
        ),
        build_running_turn_record=lambda: build_running_turn_record(
            prepared=prepared,
            owner_id=owner_id,
            runtime_claim_snapshot=service.runtime_claim_snapshot,
        ),
        create_run=lambda record: asyncio.to_thread(
            service.turn_run_store.create_run,
            record,
        ),
        reload_existing_run_after_conflict=lambda: asyncio.to_thread(
            service.turn_run_store.get_run,
            prepared.turn_context.run_id,
        ),
    )
    return await runtime.run()


async def recover_existing_running_turn(
    service: "AssistantService",
    prepared: PreparedAssistantTurn,
    *,
    existing_run,
    owner_id: uuid.UUID,
) -> None:
    if service.turn_run_store is None or existing_run.status != "running":
        return
    ensure_existing_turn_matches_request(
        prepared=prepared,
        existing_run=existing_run,
    )
    claim_state = resolve_runtime_claim_state(existing_run.runtime_claim_snapshot)
    if claim_state != "stale":
        return
    error = AssistantRuntimeTerminalError(
        code=(
            "stale_run_write_state_unknown"
            if existing_run.write_effective
            else "stale_run_interrupted"
        ),
        message=(
            "上次 turn 在写入后中断，当前不能安全重放，请刷新文稿状态后重新发起一次回复。"
            if existing_run.write_effective
            else "上次 turn 所在进程已中断，本轮已结束，请重新发起一次回复。"
        ),
        terminal_status="failed",
        write_effective=existing_run.write_effective,
    )
    record = build_terminal_turn_record(
        prepared=prepared,
        owner_id=owner_id,
        existing_run=existing_run,
        error=error,
    )
    await asyncio.to_thread(
        service.turn_run_store.save_run,
        record,
    )
    raise error


def build_running_turn_record_for_service(
    service: "AssistantService",
    prepared: PreparedAssistantTurn,
    *,
    owner_id: uuid.UUID,
    state_version: int = 1,
    provider_continuation_state: dict[str, Any] | None = None,
    pending_tool_calls_snapshot: tuple[dict[str, Any], ...] = (),
    write_effective: bool = False,
    started_at: datetime | None = None,
    updated_at: datetime | None = None,
    runtime_claim_snapshot: dict[str, Any] | None = None,
):
    return build_running_turn_record(
        prepared=prepared,
        owner_id=owner_id,
        state_version=state_version,
        provider_continuation_state=provider_continuation_state,
        pending_tool_calls_snapshot=pending_tool_calls_snapshot,
        write_effective=write_effective,
        started_at=started_at,
        updated_at=updated_at,
        runtime_claim_snapshot=runtime_claim_snapshot or service.runtime_claim_snapshot,
    )


async def run_prepare_on_error_hooks(
    service: "AssistantService",
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    hooks: list[HookConfig],
    error: Exception,
    owner_id: uuid.UUID,
) -> Exception | None:
    from .hooks_runtime.assistant_hook_runtime_support import run_prepare_on_error_hooks

    return await run_prepare_on_error_hooks(
        db,
        payload,
        hooks=hooks,
        error=error,
        owner_id=owner_id,
        run_on_error_hooks=service._run_on_error_hooks,
    )


async def run_prepared_on_error_hooks(
    service: "AssistantService",
    db: AsyncSession,
    prepared: PreparedAssistantTurn,
    *,
    error: Exception,
    owner_id: uuid.UUID,
) -> Exception | None:
    from .hooks_runtime.assistant_hook_runtime_support import run_prepared_on_error_hooks

    return await run_prepared_on_error_hooks(
        db,
        prepared,
        error=error,
        owner_id=owner_id,
        run_on_error_hooks=service._run_on_error_hooks,
    )


async def run_before_turn_hooks(
    service: "AssistantService",
    db: AsyncSession,
    prepared: PreparedAssistantTurn,
    *,
    owner_id: uuid.UUID,
) -> list[AssistantHookResultDTO]:
    from .hooks_runtime.assistant_hook_runtime_support import run_before_turn_hooks

    return await run_before_turn_hooks(
        db,
        prepared,
        owner_id=owner_id,
        run_hook_event=service._run_hook_event,
    )


async def finalize_turn(
    service: "AssistantService",
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    prepared: PreparedAssistantTurn,
    raw_output: dict[str, Any],
    *,
    before_results: list[AssistantHookResultDTO],
    owner_id: uuid.UUID,
) -> AssistantTurnResponseDTO:
    runtime = AssistantTurnFinalizeRuntime(
        resolve_content=lambda: require_text_output(raw_output.get("content")),
        build_after_payload=lambda content: build_after_assistant_payload(
            prepared.spec,
            payload,
            prepared.project_id,
            prepared.turn_context,
            content,
            visible_tool_descriptors=prepared.visible_tool_descriptors,
        ),
        run_after_hooks=lambda after_payload: service._run_hook_event(
            db,
            prepared.hooks,
            "after_assistant_response",
            payload=after_payload,
            owner_id=owner_id,
            project_id=prepared.project_id,
            agent_id=prepared.spec.agent_id,
            skill_id=prepared.spec.skill_id,
            assistant_model=prepared.spec.model,
        ),
        build_response=lambda content, after_results: build_turn_response(
            prepared.spec,
            raw_output,
            content,
            before_results + after_results,
            prepared.turn_context,
        ),
    )
    return await runtime.run()


def build_stream_event_data(
    service: "AssistantService",
    prepared: PreparedAssistantTurn,
    *,
    event_seq: int,
    extra: dict[str, Any] | None = None,
) -> LLMGenerateToolResponse:
    payload: dict[str, Any] = {
        "run_id": str(prepared.turn_context.run_id),
        "conversation_id": prepared.turn_context.conversation_id,
        "client_turn_id": prepared.turn_context.client_turn_id,
        "event_seq": event_seq,
        "state_version": resolve_stream_state_version(
            service,
            prepared.turn_context.run_id,
            fallback=event_seq,
        ),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    return payload


def resolve_stream_state_version(
    service: "AssistantService",
    run_id: uuid.UUID,
    *,
    fallback: int,
) -> int:
    if service.turn_run_store is None:
        return fallback
    record = service.turn_run_store.get_run(run_id)
    if record is None:
        return fallback
    return record.state_version


async def store_terminal_turn(
    service: "AssistantService",
    prepared: PreparedAssistantTurn,
    *,
    owner_id: uuid.UUID,
    response: AssistantTurnResponseDTO | None = None,
    error: Exception | None = None,
) -> None:
    if service.turn_run_store is None:
        return
    runtime = AssistantTurnTerminalPersistRuntime(
        resolve_existing_run=lambda: asyncio.to_thread(
            service.turn_run_store.get_run,
            prepared.turn_context.run_id,
        ),
        build_terminal_record=lambda existing_run: build_terminal_turn_record(
            prepared=prepared,
            owner_id=owner_id,
            existing_run=existing_run,
            response=response,
            error=error,
        ),
        save_run=lambda record: asyncio.to_thread(
            service.turn_run_store.save_run,
            record,
        ),
    )
    await runtime.run()
