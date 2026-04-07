from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import re
from typing import Any

from app.modules.config_registry.schemas import SkillConfig
from app.modules.project.service.project_document_support import (
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH,
    CHARACTER_SETTING_DOCUMENT_PATH,
    CHARACTERS_DATA_DOCUMENT_PATH,
    CHAPTER_PLAN_DOCUMENT_PATH,
    EVENTS_DATA_DOCUMENT_PATH,
    FACTION_RELATIONS_DATA_DOCUMENT_PATH,
    FACTION_SETTING_DOCUMENT_PATH,
    FACTIONS_DATA_DOCUMENT_PATH,
    FORESHADOWING_DOCUMENT_PATH,
    MEMBERSHIPS_DATA_DOCUMENT_PATH,
    TIMELINE_CHANGE_LOG_DOCUMENT_PATH,
    TIMELINE_INDEX_DOCUMENT_PATH,
    TURNING_POINTS_DOCUMENT_PATH,
)
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.token_counter import TokenCounter

from .assistant_prompt_render_support import render_prompt
from .assistant_prompt_support import (
    build_document_context_injection_snapshot,
    is_document_context_projection_collapsed,
    resolve_document_context_projection_mode,
)
from ..assistant_compaction_contract_support import (
    build_compaction_budget_exhausted_error,
    resolve_initial_prompt_compaction_level,
)
from .assistant_input_budget_support import (
    estimate_assistant_request_tokens,
    trim_text_to_token_budget,
)
from ..assistant_run_budget import AssistantRunBudget
from ..dto import (
    AssistantCompactionSnapshotDTO,
    AssistantMessageDTO,
    AssistantTurnRequestDTO,
    build_turn_messages_digest,
)

COMPACTION_RECENT_HISTORY_CANDIDATES = (4, 2, 0)
COMPACTION_MIN_SUMMARY_TOKENS = 8
COMPACTION_MAX_SUMMARY_TOKENS = 256
COMPACTION_KEYWORDS = (
    "人物关系",
    "势力关系",
    "隶属关系",
    "人物",
    "角色",
    "势力",
    "阵营",
    "派系",
    "主线",
    "支线",
    "伏笔",
    "线索",
    "暗线",
    "时间轴",
    "时间线",
    "事件",
    "因果",
    "冲突",
    "秘密",
    "身份",
    "动机",
    "目标",
    "回收",
    "贯穿",
)
PRIMARY_COMPACTION_KEYWORDS = frozenset(
    {
        "人物关系",
        "势力关系",
        "隶属关系",
        "主线",
        "伏笔",
        "线索",
        "时间轴",
        "时间线",
        "事件",
        "因果",
        "贯穿",
    }
)
CRITICAL_DOCUMENT_PATHS = frozenset(
    {
        CHARACTER_SETTING_DOCUMENT_PATH,
        FACTION_SETTING_DOCUMENT_PATH,
        FORESHADOWING_DOCUMENT_PATH,
        CHARACTERS_DATA_DOCUMENT_PATH,
        FACTIONS_DATA_DOCUMENT_PATH,
        CHARACTER_RELATIONS_DATA_DOCUMENT_PATH,
        FACTION_RELATIONS_DATA_DOCUMENT_PATH,
        MEMBERSHIPS_DATA_DOCUMENT_PATH,
        EVENTS_DATA_DOCUMENT_PATH,
        CHAPTER_PLAN_DOCUMENT_PATH,
        TURNING_POINTS_DOCUMENT_PATH,
        TIMELINE_INDEX_DOCUMENT_PATH,
        TIMELINE_CHANGE_LOG_DOCUMENT_PATH,
    }
)
DOCUMENT_PATH_PATTERN = re.compile(r"[\w\u4e00-\u9fff./-]+\.(?:md|json)")
DEFAULT_TOKEN_MODEL = "default"


@dataclass(frozen=True)
class AssistantPromptProjection:
    prompt: str
    compaction_snapshot: dict[str, Any] | None = None


def resolve_assistant_prompt_projection(
    *,
    template_renderer: SkillTemplateRenderer,
    skill: SkillConfig | None,
    payload: AssistantTurnRequestDTO,
    document_context: dict[str, Any] | None,
    document_context_injection_snapshot: dict[str, Any] | None,
    document_context_recovery_snapshot: dict[str, Any] | None,
    tool_guidance_snapshot: dict[str, Any] | None,
    document_context_bindings: list[dict[str, Any]],
    system_prompt: str | None,
    run_budget: AssistantRunBudget | None,
    tool_schemas: list[dict[str, Any]] | None = None,
    token_counter: TokenCounter | None = None,
) -> AssistantPromptProjection:
    counter = token_counter or TokenCounter()
    full_prompt = render_prompt(
        template_renderer=template_renderer,
        skill=skill,
        payload=payload,
        document_context_injection_snapshot=document_context_injection_snapshot,
        tool_guidance_snapshot=tool_guidance_snapshot,
    )
    max_input_tokens = None if run_budget is None else run_budget.max_input_tokens
    if max_input_tokens is None:
        return AssistantPromptProjection(prompt=full_prompt)
    estimated_full_tokens = estimate_prompt_tokens(
        prompt=full_prompt,
        system_prompt=system_prompt,
        tools=tool_schemas,
        token_counter=counter,
    )
    if estimated_full_tokens <= max_input_tokens:
        return AssistantPromptProjection(prompt=full_prompt)
    referenced_variables = _resolve_referenced_variables(template_renderer, skill)
    if "messages_json" in referenced_variables:
        raise build_compaction_budget_exhausted_error()
    history_messages = list(payload.messages[:-1])
    if not history_messages:
        raise build_compaction_budget_exhausted_error()
    protected_document_reasons = _collect_protected_document_reasons(
        payload.document_context.model_dump(mode="json") if payload.document_context is not None else None,
        document_context_bindings=document_context_bindings,
        messages=history_messages,
    )
    protected_document_paths = tuple(sorted(protected_document_reasons))
    protected_document_refs = _collect_protected_document_refs(
        payload.document_context.model_dump(mode="json") if payload.document_context is not None else None,
        document_context_bindings=document_context_bindings,
        protected_document_paths=protected_document_paths,
    )
    protected_document_binding_versions = _collect_protected_document_binding_versions(
        payload.document_context.model_dump(mode="json") if payload.document_context is not None else None,
        document_context_bindings=document_context_bindings,
        protected_document_paths=protected_document_paths,
    )
    projected_document_context_snapshot = (
        dict(document_context_injection_snapshot)
        if isinstance(document_context_injection_snapshot, dict)
        else build_document_context_injection_snapshot(
            document_context,
            document_context_recovery_snapshot=document_context_recovery_snapshot,
        )
    )
    for preserved_count in _resolve_recent_history_candidates(len(history_messages)):
        compacted_messages = history_messages[:-preserved_count] if preserved_count else history_messages
        if not compacted_messages:
            continue
        projected_history = [] if preserved_count == 0 else history_messages[-preserved_count:]
        projected_messages = [*projected_history, payload.messages[-1]]
        for summary_token_budget in _resolve_summary_token_budgets(max_input_tokens):
            summary_anchor_keywords = _build_summary_anchor_keywords(
                compacted_messages,
                protected_document_paths=protected_document_paths,
            )
            summary = _build_compacted_summary(
                compacted_messages,
                protected_document_paths=protected_document_paths,
                anchor_keywords=summary_anchor_keywords,
                target_tokens=summary_token_budget,
                token_counter=counter,
            )
            compacted_prompt = render_prompt(
                template_renderer=template_renderer,
                skill=skill,
                payload=payload,
                document_context_injection_snapshot=projected_document_context_snapshot,
                tool_guidance_snapshot=tool_guidance_snapshot,
                projected_messages=projected_messages,
                compacted_context_summary=summary,
            )
            estimated_compacted_tokens = estimate_prompt_tokens(
                prompt=compacted_prompt,
                system_prompt=system_prompt,
                tools=tool_schemas,
                token_counter=counter,
            )
            if estimated_compacted_tokens > max_input_tokens:
                continue
            snapshot = AssistantCompactionSnapshotDTO(
                trigger_reason="max_input_tokens_exceeded",
                phase="initial_prompt",
                level=resolve_initial_prompt_compaction_level(
                    preserved_recent_message_count=preserved_count
                ),
                budget_limit_tokens=max_input_tokens,
                estimated_tokens_before=estimated_full_tokens,
                estimated_tokens_after=estimated_compacted_tokens,
                compressed_message_count=len(compacted_messages),
                compressed_messages_digest=build_turn_messages_digest(compacted_messages),
                projected_messages_digest=build_turn_messages_digest(projected_messages),
                preserved_recent_message_count=preserved_count,
                summary_anchor_keywords=list(summary_anchor_keywords),
                protected_document_paths=list(protected_document_paths),
                protected_document_refs=list(protected_document_refs),
                protected_document_reasons=dict(protected_document_reasons),
                protected_document_binding_versions=dict(protected_document_binding_versions),
                document_context_collapsed=is_document_context_projection_collapsed(
                    document_context_recovery_snapshot,
                    projected_document_context_snapshot,
                ),
                document_context_projection_mode=resolve_document_context_projection_mode(
                    projected_document_context_snapshot
                ),
                projected_document_context_snapshot=(
                    dict(projected_document_context_snapshot)
                    if isinstance(projected_document_context_snapshot, dict)
                    else None
                ),
                document_context_recovery_snapshot=(
                    dict(document_context_recovery_snapshot)
                    if isinstance(document_context_recovery_snapshot, dict)
                    else None
                ),
                summary=summary,
            )
            return AssistantPromptProjection(
                prompt=compacted_prompt,
                compaction_snapshot=snapshot.model_dump(mode="json"),
            )
    raise build_compaction_budget_exhausted_error()


def estimate_prompt_tokens(
    *,
    prompt: str,
    system_prompt: str | None,
    tools: list[dict[str, Any]] | None = None,
    continuation_items: list[dict[str, Any]] | None = None,
    token_counter: TokenCounter,
) -> int:
    return estimate_assistant_request_tokens(
        prompt=prompt,
        system_prompt=system_prompt,
        token_counter=token_counter,
        tools=tools,
        continuation_items=continuation_items,
    )


def _resolve_referenced_variables(
    template_renderer: SkillTemplateRenderer,
    skill: SkillConfig | None,
) -> set[str]:
    if skill is None:
        return set()
    return template_renderer.referenced_variables(skill.prompt)


def _resolve_recent_history_candidates(history_count: int) -> tuple[int, ...]:
    candidates = []
    for value in COMPACTION_RECENT_HISTORY_CANDIDATES:
        normalized = min(value, history_count)
        if normalized not in candidates:
            candidates.append(normalized)
    return tuple(candidates)


def _resolve_summary_token_budgets(max_input_tokens: int) -> tuple[int, ...]:
    primary = max(COMPACTION_MIN_SUMMARY_TOKENS, min(COMPACTION_MAX_SUMMARY_TOKENS, max_input_tokens // 4))
    secondary = max(COMPACTION_MIN_SUMMARY_TOKENS, min(COMPACTION_MAX_SUMMARY_TOKENS, max_input_tokens // 6))
    fallback = max(COMPACTION_MIN_SUMMARY_TOKENS, min(COMPACTION_MAX_SUMMARY_TOKENS, ceil(max_input_tokens / 10)))
    compact_floor = max(COMPACTION_MIN_SUMMARY_TOKENS, min(COMPACTION_MAX_SUMMARY_TOKENS, max_input_tokens // 12))
    ordered: list[int] = []
    for candidate in (primary, secondary, fallback, compact_floor, COMPACTION_MIN_SUMMARY_TOKENS):
        if candidate not in ordered:
            ordered.append(candidate)
    return tuple(ordered)


def _collect_protected_document_reasons(
    document_context: dict[str, Any] | None,
    *,
    document_context_bindings: list[dict[str, Any]],
    messages: list[AssistantMessageDTO],
) -> dict[str, list[str]]:
    reasons: dict[str, set[str]] = {}

    def _add_reason(path: str | None, reason: str) -> None:
        if not path:
            return
        reasons.setdefault(path, set()).add(reason)

    if isinstance(document_context, dict):
        for path in _read_string_list(document_context.get("selected_paths")):
            _add_reason(path, "selected_path")
        active_path = _read_optional_string(document_context.get("active_path"))
        if active_path:
            _add_reason(active_path, "active_path")
    for binding in document_context_bindings:
        path = _read_optional_string(binding.get("path"))
        if path:
            _add_reason(path, "binding")
    for message in messages:
        for path in DOCUMENT_PATH_PATTERN.findall(message.content):
            _add_reason(path, "message_reference")
    protected: dict[str, list[str]] = {}
    for path, path_reasons in sorted(reasons.items()):
        if path in CRITICAL_DOCUMENT_PATHS:
            path_reasons.add("critical_path")
        if path.startswith("数据层/"):
            path_reasons.add("data_layer_path")
        if "critical_path" not in path_reasons and "data_layer_path" not in path_reasons:
            continue
        protected[path] = sorted(path_reasons)
    return protected


def _collect_protected_document_refs(
    document_context: dict[str, Any] | None,
    *,
    document_context_bindings: list[dict[str, Any]],
    protected_document_paths: tuple[str, ...],
) -> tuple[str, ...]:
    if not protected_document_paths:
        return ()
    protected_path_set = set(protected_document_paths)
    refs: set[str] = set()
    if isinstance(document_context, dict):
        active_path = _read_optional_string(document_context.get("active_path"))
        active_document_ref = _read_optional_string(document_context.get("active_document_ref"))
        if active_path in protected_path_set and active_document_ref:
            refs.add(active_document_ref)
        for path, document_ref in zip(
            _read_string_list(document_context.get("selected_paths")),
            _read_string_list(document_context.get("selected_document_refs")),
            strict=False,
        ):
            if path in protected_path_set and document_ref:
                refs.add(document_ref)
    for binding in document_context_bindings:
        path = _read_optional_string(binding.get("path"))
        document_ref = _read_optional_string(binding.get("document_ref"))
        if path in protected_path_set and document_ref:
            refs.add(document_ref)
    return tuple(sorted(refs))


def _collect_protected_document_binding_versions(
    document_context: dict[str, Any] | None,
    *,
    document_context_bindings: list[dict[str, Any]],
    protected_document_paths: tuple[str, ...],
) -> dict[str, str]:
    if not protected_document_paths:
        return {}
    protected_path_set = set(protected_document_paths)
    binding_versions: dict[str, str] = {}
    if isinstance(document_context, dict):
        active_path = _read_optional_string(document_context.get("active_path"))
        active_document_ref = _read_optional_string(document_context.get("active_document_ref"))
        active_binding_version = _read_optional_string(document_context.get("active_binding_version"))
        if (
            active_path in protected_path_set
            and active_document_ref is not None
            and active_binding_version is not None
        ):
            binding_versions[active_document_ref] = active_binding_version
    for binding in document_context_bindings:
        path = _read_optional_string(binding.get("path"))
        document_ref = _read_optional_string(binding.get("document_ref"))
        binding_version = _read_optional_string(binding.get("binding_version"))
        if path in protected_path_set and document_ref is not None and binding_version is not None:
            binding_versions[document_ref] = binding_version
    return dict(sorted(binding_versions.items()))


def _build_compacted_summary(
    messages: list[AssistantMessageDTO],
    *,
    protected_document_paths: tuple[str, ...],
    anchor_keywords: list[str] | None = None,
    target_tokens: int,
    token_counter: TokenCounter,
) -> str:
    sections: list[str] = []
    resolved_anchor_keywords = (
        list(anchor_keywords)
        if anchor_keywords is not None
        else _build_summary_anchor_keywords(
            messages,
            protected_document_paths=protected_document_paths,
        )
    )
    if resolved_anchor_keywords:
        sections.append("连续性锚点：" + "、".join(resolved_anchor_keywords))
    excerpts = _collect_priority_excerpts(messages)
    if excerpts:
        sections.append("高优先级连续性信息：\n" + "\n".join(f"- {item}" for item in excerpts))
    if protected_document_paths:
        sections.append("关键文稿锚点：" + "、".join(protected_document_paths))
    sections.append("较早对话摘要：\n" + "\n".join(f"- {item}" for item in _build_message_abstracts(messages)))
    summary = "\n\n".join(section for section in sections if section.strip())
    return _trim_text_to_token_budget(summary, target_tokens=target_tokens, token_counter=token_counter)


def _build_summary_anchor_keywords(
    messages: list[AssistantMessageDTO],
    *,
    protected_document_paths: tuple[str, ...],
) -> list[str]:
    corpus = "\n".join(message.content for message in messages)
    path_text = "\n".join(protected_document_paths)
    anchors: list[str] = []
    for keyword in ("人物关系", "势力关系", "贯穿全文", "时间轴", "伏笔", "主线", "因果"):
        if keyword in corpus or keyword in path_text:
            anchors.append(keyword)
    return anchors


def _collect_priority_excerpts(messages: list[AssistantMessageDTO]) -> list[str]:
    excerpts: list[str] = []
    covered_keywords: set[str] = set()
    covered_primary_keywords: set[str] = set()
    for message in messages:
        for sentence in _split_message_sentences(message.content):
            matched_keywords = {keyword for keyword in COMPACTION_KEYWORDS if keyword in sentence}
            if not matched_keywords:
                continue
            primary_matches = matched_keywords & PRIMARY_COMPACTION_KEYWORDS
            if primary_matches:
                if primary_matches.issubset(covered_primary_keywords):
                    continue
            elif len(covered_primary_keywords) < 2:
                continue
            elif excerpts and matched_keywords.issubset(covered_keywords):
                continue
            excerpt = f"{_resolve_role_label(message)}：{_truncate_priority_sentence(sentence, 80)}"
            if excerpt not in excerpts:
                excerpts.append(excerpt)
                covered_keywords.update(matched_keywords)
                covered_primary_keywords.update(primary_matches)
            if len(excerpts) >= 6:
                return excerpts
    return excerpts


def _build_message_abstracts(messages: list[AssistantMessageDTO]) -> list[str]:
    return [
        f"{_resolve_role_label(message)}：{_truncate_text(_normalize_whitespace(message.content), 90)}"
        for message in messages
    ]


def _split_message_sentences(content: str) -> list[str]:
    normalized = _normalize_whitespace(content)
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？!?；;])|\n", normalized)
    return [item.strip() for item in parts if item.strip()]


def _trim_text_to_token_budget(
    text: str,
    *,
    target_tokens: int,
    token_counter: TokenCounter,
) -> str:
    return trim_text_to_token_budget(
        text,
        target_tokens=target_tokens,
        token_counter=token_counter,
    )

def _resolve_role_label(message: AssistantMessageDTO) -> str:
    return "助手" if message.role == "assistant" else "用户"


def _normalize_whitespace(content: str) -> str:
    return " ".join(content.split())


def _truncate_text(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    return content[: max(1, limit - 1)].rstrip() + "…"


def _truncate_priority_sentence(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    keyword_spans = _resolve_keyword_spans(content)
    if not keyword_spans:
        return _truncate_text(content, limit)
    start = keyword_spans[0][0]
    end = keyword_spans[-1][1]
    focused = _slice_with_ellipsis(
        content,
        start=max(0, start - 8),
        end=min(len(content), end + 8),
    )
    if len(focused) <= limit:
        return focused
    head = _slice_with_ellipsis(
        content,
        start=max(0, keyword_spans[0][0] - 6),
        end=min(len(content), keyword_spans[0][1] + 10),
    )
    tail = _slice_with_ellipsis(
        content,
        start=max(0, keyword_spans[-1][0] - 10),
        end=min(len(content), keyword_spans[-1][1] + 6),
    )
    combined = head if tail in head else f"{head} / {tail}"
    return _truncate_text(combined, limit)


def _resolve_keyword_spans(content: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for keyword in COMPACTION_KEYWORDS:
        start = content.find(keyword)
        if start < 0:
            continue
        spans.append((start, start + len(keyword)))
    return sorted(set(spans))


def _slice_with_ellipsis(content: str, *, start: int, end: int) -> str:
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{content[start:end].strip()}{suffix}"


def _read_optional_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _read_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
