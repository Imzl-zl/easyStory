from __future__ import annotations

import asyncio
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import HookConfig, ModelConfig
from app.shared.runtime import PluginRegistry, SkillTemplateRenderer

from ..agents.assistant_agent_service import AssistantAgentService
from ..assistant_execution_support import (
    build_hook_agent_variables,
    hook_agent_response_format,
    require_agent_skill,
    resolve_hook_agent_model,
    resolve_hook_agent_output,
    validate_retry_policy,
)
from .assistant_hook_support import (
    AssistantHookExecutionContext,
    matches_hook_condition,
    normalize_hook_result,
    resolve_assistant_hooks_for_event,
    serialize_hook_error,
)
from ..rules.assistant_rule_service import AssistantRuleService
from ..rules.assistant_rule_support import build_assistant_system_prompt
from ..skills.assistant_skill_service import AssistantSkillService
from ..turn.assistant_turn_error_support import (
    build_request_error_hook_payload,
    mark_on_error_hooks_run,
    on_error_hooks_already_run,
)
from ..turn.assistant_turn_runtime_support import PreparedAssistantTurn
from ..dto import AssistantHookResultDTO, AssistantTurnRequestDTO
from ..preferences.preferences_service import AssistantPreferencesService


async def run_assistant_agent_hook(
    context: AssistantHookExecutionContext,
    *,
    agent_id: str,
    input_mapping: dict[str, str],
    assistant_agent_service: AssistantAgentService,
    assistant_skill_service: AssistantSkillService,
    assistant_preferences_service: AssistantPreferencesService,
    assistant_rule_service: AssistantRuleService,
    template_renderer: SkillTemplateRenderer,
    llm_caller,
) -> Any:
    agent = assistant_agent_service.resolve_agent(
        agent_id,
        owner_id=context.owner_id,
        allow_disabled=True,
    )
    skill = require_agent_skill(
        lambda skill_id: assistant_skill_service.resolve_skill(
            skill_id,
            owner_id=context.owner_id,
            project_id=context.project_id,
            allow_disabled=True,
        ),
        agent,
    )
    variables = build_hook_agent_variables(context, input_mapping)
    prompt = template_renderer.render(skill.prompt, variables)
    preferences = await assistant_preferences_service.resolve_preferences(
        context.db,
        owner_id=context.owner_id,
        project_id=context.project_id,
    )
    model = resolve_hook_agent_model(
        agent=agent,
        skill=skill,
        preferences=preferences,
        assistant_model=context.assistant_model,
    )
    rule_bundle = await assistant_rule_service.build_rule_bundle(
        context.db,
        owner_id=context.owner_id,
        project_id=context.project_id,
    )
    system_prompt = build_assistant_system_prompt(
        agent.system_prompt,
        user_content=rule_bundle.user_content,
        project_content=rule_bundle.project_content,
    )
    raw_output = await llm_caller(
        context.db,
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        owner_id=context.owner_id,
        project_id=context.project_id,
        response_format=hook_agent_response_format(agent),
    )
    return resolve_hook_agent_output(agent, raw_output.get("content"))


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
