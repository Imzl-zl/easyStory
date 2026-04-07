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
from .assistant_input_budget_support import (
    estimate_assistant_request_tokens,
    trim_text_to_token_budget,
)
from ..assistant_run_budget import AssistantRunBudget
from ..assistant_runtime_terminal import AssistantRuntimeTerminalError
from ..dto import (
    AssistantCompactionSnapshotDTO,
    AssistantMessageDTO,
    AssistantProjectToolGuidanceDTO,
    AssistantTurnRequestDTO,
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
    project_tool_guidance: AssistantProjectToolGuidanceDTO | None,
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
        document_context=document_context,
        project_tool_guidance=project_tool_guidance,
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
        raise _build_budget_exhausted_error()
    history_messages = list(payload.messages[:-1])
    if not history_messages:
        raise _build_budget_exhausted_error()
    protected_document_paths = _collect_protected_document_paths(
        payload.document_context.model_dump(mode="json") if payload.document_context is not None else None,
        document_context_bindings=document_context_bindings,
        messages=history_messages,
    )
    for preserved_count in _resolve_recent_history_candidates(len(history_messages)):
        compacted_messages = history_messages[:-preserved_count] if preserved_count else history_messages
        if not compacted_messages:
            continue
        projected_history = [] if preserved_count == 0 else history_messages[-preserved_count:]
        projected_messages = [*projected_history, payload.messages[-1]]
        for summary_token_budget in _resolve_summary_token_budgets(max_input_tokens):
            summary = _build_compacted_summary(
                compacted_messages,
                protected_document_paths=protected_document_paths,
                target_tokens=summary_token_budget,
                token_counter=counter,
            )
            compacted_prompt = render_prompt(
                template_renderer=template_renderer,
                skill=skill,
                payload=payload,
                document_context=document_context,
                project_tool_guidance=project_tool_guidance,
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
                level=_resolve_compaction_level(preserved_count),
                budget_limit_tokens=max_input_tokens,
                estimated_tokens_before=estimated_full_tokens,
                estimated_tokens_after=estimated_compacted_tokens,
                compressed_message_count=len(compacted_messages),
                preserved_recent_message_count=preserved_count,
                protected_document_paths=list(protected_document_paths),
                summary=summary,
            )
            return AssistantPromptProjection(
                prompt=compacted_prompt,
                compaction_snapshot=snapshot.model_dump(mode="json"),
            )
    raise _build_budget_exhausted_error()


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


def _resolve_compaction_level(preserved_recent_message_count: int) -> str:
    if preserved_recent_message_count > 0:
        return "soft"
    return "hard"


def _collect_protected_document_paths(
    document_context: dict[str, Any] | None,
    *,
    document_context_bindings: list[dict[str, Any]],
    messages: list[AssistantMessageDTO],
) -> tuple[str, ...]:
    paths: set[str] = set()
    if isinstance(document_context, dict):
        paths.update(_read_string_list(document_context.get("selected_paths")))
        active_path = _read_optional_string(document_context.get("active_path"))
        if active_path:
            paths.add(active_path)
    for binding in document_context_bindings:
        path = _read_optional_string(binding.get("path"))
        if path:
            paths.add(path)
    for message in messages:
        paths.update(DOCUMENT_PATH_PATTERN.findall(message.content))
    protected = sorted(
        path
        for path in paths
        if path in CRITICAL_DOCUMENT_PATHS or path.startswith("数据层/")
    )
    return tuple(protected)


def _build_compacted_summary(
    messages: list[AssistantMessageDTO],
    *,
    protected_document_paths: tuple[str, ...],
    target_tokens: int,
    token_counter: TokenCounter,
) -> str:
    sections: list[str] = []
    anchor_keywords = _build_summary_anchor_keywords(
        messages,
        protected_document_paths=protected_document_paths,
    )
    if anchor_keywords:
        sections.append("连续性锚点：" + "、".join(anchor_keywords))
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


def _build_budget_exhausted_error() -> AssistantRuntimeTerminalError:
    return AssistantRuntimeTerminalError(
        code="budget_exhausted",
        message="本轮上下文预算已耗尽，压缩后仍无法继续执行。",
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
