from __future__ import annotations

import asyncio
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import HookConfig, ModelConfig
from app.shared.runtime.plugins.plugin_registry import PluginRegistry

from ..assistant_execution_support import (
    validate_retry_policy,
)
from .assistant_hook_support import (
    AssistantHookExecutionContext,
    matches_hook_condition,
    normalize_hook_result,
    resolve_assistant_hooks_for_event,
    serialize_hook_error,
)
from ..turn.assistant_turn_error_support import (
    build_request_error_hook_payload,
    mark_on_error_hooks_run,
    on_error_hooks_already_run,
)
from ..turn.assistant_turn_runtime_support import PreparedAssistantTurn
from ..dto import AssistantHookResultDTO, AssistantTurnRequestDTO


async def run_assistant_hook_event(
    db: AsyncSession,
    hooks: list[HookConfig],
    event: str,
    *,
    payload: dict[str, Any],
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    agent_id: str | None,
    skill_id: str | None,
    assistant_model: ModelConfig,
    execute_hook_with_retry,
) -> list[AssistantHookResultDTO]:
    context = AssistantHookExecutionContext(
        db=db,
        event=event,
        owner_id=owner_id,
        payload=payload,
        assistant_agent_id=agent_id,
        assistant_skill_id=skill_id,
        assistant_model=assistant_model,
        project_id=project_id,
    )
    results: list[AssistantHookResultDTO] = []
    for hook in resolve_assistant_hooks_for_event(hooks, event):
        if not matches_hook_condition(hook, payload):
            continue
        result = await execute_hook_with_retry(context, hook)
        results.append(
            AssistantHookResultDTO(
                event=event,
                hook_id=hook.id,
                action_type=hook.action.action_type,
                result=normalize_hook_result(result),
            )
        )
    return results


async def execute_assistant_hook_with_retry(
    context: AssistantHookExecutionContext,
    hook: HookConfig,
    *,
    plugin_registry: PluginRegistry,
) -> Any:
    attempts = hook.retry.max_attempts if hook.retry is not None else 1
    delay = hook.retry.delay if hook.retry is not None else 0
    validate_retry_policy(attempts, delay)
    for attempt in range(1, attempts + 1):
        try:
            return await plugin_registry.execute(
                hook.action.action_type,
                config=hook.action.config,
                context=context,
                timeout_seconds=hook.timeout,
            )
        except Exception:
            if attempt >= attempts:
                raise
            await asyncio.sleep(delay)
    raise RuntimeError("Hook retry loop exited unexpectedly")


async def run_prepare_on_error_hooks(
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    hooks: list[HookConfig],
    error: Exception,
    owner_id: uuid.UUID,
    run_on_error_hooks,
) -> Exception | None:
    if not hooks or on_error_hooks_already_run(error):
        return None
    try:
        await run_on_error_hooks(
            db,
            hooks,
            build_request_error_hook_payload(payload=payload, owner_id=owner_id),
            error,
            owner_id=owner_id,
            project_id=payload.project_id,
            agent_id=payload.agent_id,
            skill_id=payload.skill_id,
            assistant_model=payload.model or ModelConfig(),
        )
    except Exception as hook_error:
        return hook_error
    return None


async def run_prepared_on_error_hooks(
    db: AsyncSession,
    prepared: PreparedAssistantTurn,
    *,
    error: Exception,
    owner_id: uuid.UUID,
    run_on_error_hooks,
) -> Exception | None:
    if on_error_hooks_already_run(error):
        return None
    try:
        await run_on_error_hooks(
            db,
            prepared.hooks,
            prepared.before_payload,
            error,
            owner_id=owner_id,
            project_id=prepared.project_id,
            agent_id=prepared.spec.agent_id,
            skill_id=prepared.spec.skill_id,
            assistant_model=prepared.spec.model,
        )
    except Exception as hook_error:
        return hook_error
    return None


async def run_before_turn_hooks(
    db: AsyncSession,
    prepared: PreparedAssistantTurn,
    *,
    owner_id: uuid.UUID,
    run_hook_event,
) -> list[AssistantHookResultDTO]:
    return await run_hook_event(
        db,
        prepared.hooks,
        "before_assistant_response",
        payload=prepared.before_payload,
        owner_id=owner_id,
        project_id=prepared.project_id,
        agent_id=prepared.spec.agent_id,
        skill_id=prepared.spec.skill_id,
        assistant_model=prepared.spec.model,
    )


async def run_assistant_on_error_hooks(
    db: AsyncSession,
    hooks: list[HookConfig],
    payload: dict[str, Any],
    error: Exception,
    *,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    agent_id: str | None,
    skill_id: str | None,
    assistant_model: ModelConfig,
    run_hook_event,
) -> None:
    error_payload = dict(payload)
    error_payload["error"] = serialize_hook_error(error)
    try:
        await run_hook_event(
            db,
            hooks,
            "on_error",
            payload=error_payload,
            owner_id=owner_id,
            project_id=project_id,
            agent_id=agent_id,
            skill_id=skill_id,
            assistant_model=assistant_model,
        )
    except Exception as hook_exc:
        grouped_error = ExceptionGroup(
            "Assistant runtime error and on_error hook both failed",
            [
                mark_on_error_hooks_run(error),
                mark_on_error_hooks_run(hook_exc),
            ],
        )
        mark_on_error_hooks_run(grouped_error)
        raise grouped_error from hook_exc
    mark_on_error_hooks_run(error)
