from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import HookConfig
from app.modules.project.service import ProjectDocumentCapabilityService, ProjectService
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.errors import ConfigurationError

from ..agents.assistant_agent_service import AssistantAgentService
from ..context.assistant_context_compaction_support import resolve_assistant_prompt_projection
from ..context.assistant_document_context_support import (
    NormalizedAssistantTurnPayload,
    normalize_turn_payload,
)
from ..context.assistant_prompt_support import (
    build_document_context_injection_snapshot,
    build_project_tool_guidance_snapshot_from_discovery_decision,
    freeze_project_tool_guidance_snapshot,
    require_latest_user_message,
    resolve_project_tool_discovery_decision,
)
from ..assistant_execution_support import resolve_execution_spec
from ..hooks.assistant_hook_service import AssistantHookService
from ..assistant_llm_runtime_support import (
    ensure_assistant_runtime_supports_visible_tools,
    resolve_assistant_max_output_tokens,
)
from ..preferences.preferences_service import AssistantPreferencesService
from ..assistant_run_budget import enrich_assistant_run_budget_with_input_window
from ..rules.assistant_rule_service import AssistantRuleService
from ..rules.assistant_rule_support import build_assistant_system_prompt
from ..skills.assistant_skill_service import AssistantSkillService
from ..tooling.assistant_tool_loop import AssistantToolLoop
from ..tooling.assistant_tool_catalog_support import build_tool_catalog_version
from .assistant_turn_error_support import AssistantConversationStateMismatchError
from .assistant_turn_run_store import AssistantTurnRunStore
from .assistant_turn_runtime_support import (
    PreparedAssistantTurn,
    build_before_assistant_payload,
    build_document_context_recovery_snapshot,
    build_turn_context,
    freeze_turn_run_snapshot,
)
from ..dto import AssistantTurnRequestDTO, build_turn_messages_digest


async def prepare_assistant_turn(
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    resolved_hooks: list[HookConfig] | None,
    config_loader: ConfigLoader,
    template_renderer: SkillTemplateRenderer,
    project_service: ProjectService,
    assistant_preferences_service: AssistantPreferencesService,
    assistant_rule_service: AssistantRuleService,
    assistant_agent_service: AssistantAgentService,
    assistant_skill_service: AssistantSkillService,
    assistant_hook_service: AssistantHookService,
    assistant_tool_loop: AssistantToolLoop | None,
    turn_run_store: AssistantTurnRunStore | None,
    project_document_capability_service: ProjectDocumentCapabilityService | None,
    resolve_llm_runtime,
) -> PreparedAssistantTurn:
    project_id = await resolve_assistant_project_scope(
        db,
        project_id=payload.project_id,
        owner_id=owner_id,
        project_service=project_service,
    )
    normalized_turn_payload = await normalize_assistant_turn_payload(
        db,
        payload,
        owner_id=owner_id,
        project_id=project_id,
        project_document_capability_service=project_document_capability_service,
    )
    normalized_payload = normalized_turn_payload.payload
    validate_assistant_continuation_anchor(
        normalized_payload,
        owner_id=owner_id,
        project_id=project_id,
        turn_run_store=turn_run_store,
    )
    preferences = await assistant_preferences_service.resolve_preferences(
        db,
        owner_id=owner_id,
        project_id=project_id,
    )
    spec = resolve_execution_spec(
        config_loader,
        normalized_payload,
        preferences,
        load_agent=lambda agent_id: assistant_agent_service.resolve_agent(
            agent_id,
            owner_id=owner_id,
        ),
        load_skill=lambda skill_id: assistant_skill_service.resolve_skill(
            skill_id,
            owner_id=owner_id,
            project_id=project_id,
            allow_disabled=normalized_payload.agent_id is not None,
        ),
    )
    rule_bundle = await assistant_rule_service.build_rule_bundle(
        db,
        owner_id=owner_id,
        project_id=project_id,
    )
    system_prompt = build_assistant_system_prompt(
        spec.system_prompt,
        user_content=rule_bundle.user_content,
        project_content=rule_bundle.project_content,
    )
    document_context_recovery_snapshot = build_document_context_recovery_snapshot(
        document_context=(
            normalized_payload.document_context.model_dump(mode="json")
            if normalized_payload.document_context is not None
            else None
        ),
        document_context_bindings=normalized_turn_payload.document_context_bindings,
    )
    document_context_injection_snapshot = build_document_context_injection_snapshot(
        (
            normalized_payload.document_context.model_dump(mode="json")
            if normalized_payload.document_context is not None
            else None
        ),
        document_context_recovery_snapshot=document_context_recovery_snapshot,
    )
    provisional_turn_context = build_turn_context(
        spec,
        normalized_payload,
        document_context_recovery_snapshot=document_context_recovery_snapshot,
        document_context_injection_snapshot=document_context_injection_snapshot,
        document_context_bindings=normalized_turn_payload.document_context_bindings,
        tool_guidance_snapshot=None,
        owner_id=owner_id,
        project_id=project_id,
        tool_catalog_version=None,
        user_rule_content=rule_bundle.user_content,
        project_rule_content=rule_bundle.project_content,
    )
    tool_policy_decisions, visible_tool_descriptors, run_budget = resolve_assistant_tool_policy_bundle(
        assistant_tool_loop=assistant_tool_loop,
        turn_context=provisional_turn_context,
        project_id=project_id,
    )
    resolved_llm_runtime = await resolve_llm_runtime(
        db,
        model=spec.model,
        owner_id=owner_id,
        project_id=project_id,
    )
    ensure_assistant_runtime_supports_visible_tools(
        resolved_llm_runtime,
        visible_tool_names=tuple(item.name for item in visible_tool_descriptors),
        stream_output=normalized_payload.stream,
    )
    tool_schemas = resolve_assistant_tool_schemas(
        assistant_tool_loop=assistant_tool_loop,
        turn_context=provisional_turn_context,
        project_id=project_id,
        visible_tool_descriptors=visible_tool_descriptors,
    )
    tool_guidance_snapshot = freeze_project_tool_guidance_snapshot(
        build_project_tool_guidance_snapshot_from_discovery_decision(
            resolve_project_tool_discovery_decision(
                has_project_scope=project_id is not None,
                visible_tool_names=tuple(item.name for item in visible_tool_descriptors),
                latest_user_message=require_latest_user_message(normalized_payload.messages),
                document_context=(
                    normalized_payload.document_context.model_dump(mode="json")
                    if normalized_payload.document_context is not None
                    else None
                ),
            )
        )
    )
    run_budget = enrich_assistant_run_budget_with_input_window(
        run_budget,
        context_window_tokens=resolved_llm_runtime.context_window_tokens,
        max_output_tokens=resolve_assistant_max_output_tokens(
            spec.model,
            resolved_runtime=resolved_llm_runtime,
        ),
    )
    prompt_projection = resolve_assistant_prompt_projection(
        template_renderer=template_renderer,
        skill=spec.skill,
        payload=normalized_payload,
        document_context=(
            normalized_payload.document_context.model_dump(mode="json")
            if normalized_payload.document_context is not None
            else None
        ),
        document_context_injection_snapshot=document_context_injection_snapshot,
        document_context_recovery_snapshot=document_context_recovery_snapshot,
        tool_guidance_snapshot=tool_guidance_snapshot,
        document_context_bindings=normalized_turn_payload.document_context_bindings,
        system_prompt=system_prompt,
        run_budget=run_budget,
        tool_schemas=tool_schemas,
    )
    tool_catalog_version = resolve_assistant_tool_catalog_version(
        assistant_tool_loop=assistant_tool_loop,
        visible_tool_descriptors=visible_tool_descriptors,
    )
    turn_context = build_turn_context(
        spec,
        normalized_payload,
        compaction_snapshot=prompt_projection.compaction_snapshot,
        document_context_recovery_snapshot=document_context_recovery_snapshot,
        document_context_injection_snapshot=document_context_injection_snapshot,
        document_context_bindings=normalized_turn_payload.document_context_bindings,
        tool_guidance_snapshot=tool_guidance_snapshot,
        owner_id=owner_id,
        project_id=project_id,
        tool_catalog_version=tool_catalog_version,
        user_rule_content=rule_bundle.user_content,
        project_rule_content=rule_bundle.project_content,
    )
    return PreparedAssistantTurn(
        before_payload=build_before_assistant_payload(
            spec,
            normalized_payload,
            project_id,
            turn_context,
            visible_tool_descriptors=visible_tool_descriptors,
        ),
        hooks=list(
            resolved_hooks
            if resolved_hooks is not None
            else resolve_requested_hooks(
                assistant_hook_service=assistant_hook_service,
                hook_ids=normalized_payload.hook_ids,
                owner_id=owner_id,
            )
        ),
        project_id=project_id,
        prompt=prompt_projection.prompt,
        run_budget=run_budget,
        resolved_llm_runtime=resolved_llm_runtime,
        spec=spec,
        system_prompt=system_prompt,
        turn_context=turn_context,
        run_snapshot=freeze_turn_run_snapshot(
            turn_context,
            tool_policy_decisions=tool_policy_decisions,
            budget=run_budget,
        ),
        tool_policy_decisions=tool_policy_decisions,
        visible_tool_descriptors=visible_tool_descriptors,
    )


def resolve_requested_hooks(
    *,
    assistant_hook_service: AssistantHookService,
    hook_ids: list[str],
    owner_id: uuid.UUID,
) -> list[HookConfig]:
    return [
        assistant_hook_service.resolve_hook(hook_id, owner_id=owner_id)
        for hook_id in hook_ids
    ]


async def normalize_assistant_turn_payload(
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    project_document_capability_service: ProjectDocumentCapabilityService | None,
) -> NormalizedAssistantTurnPayload:
    return await normalize_turn_payload(
        db,
        payload,
        owner_id=owner_id,
        project_id=project_id,
        project_document_capability_service=project_document_capability_service,
    )


def validate_assistant_continuation_anchor(
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    turn_run_store: AssistantTurnRunStore | None,
) -> None:
    anchor = payload.continuation_anchor
    if anchor is None:
        return
    if turn_run_store is None:
        raise ConfigurationError("Assistant turn run store is not configured")
    previous_run = turn_run_store.get_run(anchor.previous_run_id)
    if previous_run is None or previous_run.terminal_status != "completed":
        raise AssistantConversationStateMismatchError()
    direct_parent_digest = build_turn_messages_digest(payload.messages[:-1])
    if (
        previous_run.owner_id != owner_id
        or previous_run.project_id != project_id
        or previous_run.conversation_id != payload.conversation_id
        or previous_run.completion_messages_digest != direct_parent_digest
    ):
        raise AssistantConversationStateMismatchError()


async def resolve_assistant_project_scope(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None,
    owner_id: uuid.UUID,
    project_service: ProjectService,
) -> uuid.UUID | None:
    if project_id is None:
        return None
    return (await project_service.require_project(db, project_id, owner_id=owner_id)).id


def resolve_assistant_tool_policy_bundle(
    *,
    assistant_tool_loop: AssistantToolLoop | None,
    turn_context,
    project_id: uuid.UUID | None,
) -> tuple[tuple[Any, ...], tuple[Any, ...], Any | None]:
    if assistant_tool_loop is None:
        return (), (), None
    return assistant_tool_loop.resolve_policy_bundle(
        turn_context=turn_context,
        project_id=project_id,
    )


def resolve_assistant_tool_schemas(
    *,
    assistant_tool_loop: AssistantToolLoop | None,
    turn_context,
    project_id: uuid.UUID | None,
    visible_tool_descriptors,
) -> list[dict[str, Any]]:
    if assistant_tool_loop is None:
        return []
    return assistant_tool_loop.resolve_tool_schemas(
        turn_context=turn_context,
        project_id=project_id,
        visible_descriptors=visible_tool_descriptors,
    )


def resolve_assistant_tool_catalog_version(
    *,
    assistant_tool_loop: AssistantToolLoop | None,
    visible_tool_descriptors,
) -> str | None:
    del assistant_tool_loop
    return build_tool_catalog_version(visible_tool_descriptors)
