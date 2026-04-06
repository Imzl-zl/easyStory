from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from .project_document_capability_dto import (
    ProjectDocumentContentState,
    ProjectDocumentSearchField,
    ProjectDocumentSearchHitDTO,
)
from .project_document_catalog_support import (
    ResolvedProjectDocumentCatalogRecord,
    _build_binding_version,
    _resolve_visible_content_state,
)
from .project_document_support import (
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH,
    CHARACTER_SETTING_DOCUMENT_PATH,
    CHARACTERS_DATA_DOCUMENT_PATH,
    CHRONICLE_DOCUMENT_PATH,
    EVENTS_DATA_DOCUMENT_PATH,
    FACTION_RELATIONS_DATA_DOCUMENT_PATH,
    FACTION_SETTING_DOCUMENT_PATH,
    FACTIONS_DATA_DOCUMENT_PATH,
    FORESHADOWING_CHECKLIST_DOCUMENT_PATH,
    FORESHADOWING_DOCUMENT_PATH,
    MEMBERSHIPS_DATA_DOCUMENT_PATH,
    TIMELINE_CHANGE_LOG_DOCUMENT_PATH,
    TIMELINE_INDEX_DOCUMENT_PATH,
)

PROJECT_DOCUMENT_SEARCH_DEFAULT_LIMIT = 8
PROJECT_DOCUMENT_SEARCH_MAX_LIMIT = 20
PROJECT_DOCUMENT_SEARCH_TERM_SEPARATOR = re.compile(r"[\s/_.:-]+")
PROJECT_DOCUMENT_SEARCH_FIELD_ORDER: tuple[ProjectDocumentSearchField, ...] = (
    "path",
    "title",
    "schema_id",
    "source",
    "document_kind",
    "content_state",
)
PROJECT_DOCUMENT_SEARCH_FIELD_WEIGHTS: dict[ProjectDocumentSearchField, int] = {
    "path": 12,
    "title": 10,
    "schema_id": 8,
    "source": 6,
    "document_kind": 4,
    "content_state": 2,
}
PROJECT_DOCUMENT_SEARCH_QUERY_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "连续性": ("人物关系", "势力关系", "时间轴", "事件", "伏笔", "章节索引", "状态变更", "年表"),
    "一致性": ("人物关系", "势力关系", "时间轴", "事件", "伏笔"),
    "角色": ("人物",),
    "角色关系": ("人物关系",),
    "阵营": ("势力",),
    "阵营关系": ("势力关系",),
    "时间线": ("时间轴", "事件", "年表", "章节索引", "状态变更"),
    "伏线": ("伏笔", "回收"),
    "回收": ("伏笔", "伏笔回收"),
}
PROJECT_DOCUMENT_SEARCH_QUERY_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "continuity": ("连续性", "一致性", "设定一致性", "贯穿全文"),
    "characters": ("人物", "角色"),
    "character_relations": ("人物关系", "角色关系"),
    "factions": ("势力", "阵营"),
    "faction_relations": ("势力关系", "阵营关系", "隶属关系"),
    "timeline": ("时间轴", "时间线", "章节索引", "状态变更", "年表"),
    "events": ("事件", "主线事件"),
    "foreshadowing": ("伏笔", "伏线", "回收"),
}
PROJECT_DOCUMENT_SEARCH_INTENT_WEIGHTS: dict[str, int] = {
    "continuity": 8,
    "characters": 6,
    "character_relations": 10,
    "factions": 6,
    "faction_relations": 10,
    "timeline": 8,
    "events": 6,
    "foreshadowing": 8,
}
PROJECT_DOCUMENT_SEARCH_PATH_INTENTS: dict[str, frozenset[str]] = {
    CHARACTER_SETTING_DOCUMENT_PATH: frozenset({"characters"}),
    FACTION_SETTING_DOCUMENT_PATH: frozenset({"factions"}),
    CHARACTERS_DATA_DOCUMENT_PATH: frozenset({"characters"}),
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH: frozenset({"characters", "character_relations", "continuity"}),
    FACTIONS_DATA_DOCUMENT_PATH: frozenset({"factions"}),
    FACTION_RELATIONS_DATA_DOCUMENT_PATH: frozenset({"factions", "faction_relations", "continuity"}),
    MEMBERSHIPS_DATA_DOCUMENT_PATH: frozenset({"characters", "factions", "faction_relations", "continuity"}),
    EVENTS_DATA_DOCUMENT_PATH: frozenset({"timeline", "events", "continuity"}),
    TIMELINE_INDEX_DOCUMENT_PATH: frozenset({"timeline", "events", "continuity"}),
    TIMELINE_CHANGE_LOG_DOCUMENT_PATH: frozenset({"timeline", "events", "continuity"}),
    CHRONICLE_DOCUMENT_PATH: frozenset({"timeline", "events"}),
    FORESHADOWING_DOCUMENT_PATH: frozenset({"foreshadowing", "continuity"}),
    FORESHADOWING_CHECKLIST_DOCUMENT_PATH: frozenset({"foreshadowing", "continuity"}),
}


@dataclass(frozen=True)
class ProjectDocumentCatalogSearchMatch:
    matched_fields: tuple[ProjectDocumentSearchField, ...]
    match_score: int


def _validate_search_limit(limit: int) -> None:
    if PROJECT_DOCUMENT_SEARCH_DEFAULT_LIMIT <= 0:
        raise RuntimeError("PROJECT_DOCUMENT_SEARCH_DEFAULT_LIMIT must be positive")
    if PROJECT_DOCUMENT_SEARCH_MAX_LIMIT < PROJECT_DOCUMENT_SEARCH_DEFAULT_LIMIT:
        raise RuntimeError("PROJECT_DOCUMENT_SEARCH_MAX_LIMIT must cover default limit")
    if limit < 1 or limit > PROJECT_DOCUMENT_SEARCH_MAX_LIMIT:
        raise ValueError(
            f"limit must be between 1 and {PROJECT_DOCUMENT_SEARCH_MAX_LIMIT}"
        )


def _validate_search_request(
    *,
    query: str | None,
    path_prefix: str | None,
    allowed_sources: frozenset[str],
    allowed_schema_ids: frozenset[str],
    allowed_content_states: frozenset[ProjectDocumentContentState],
    writable: bool | None,
) -> None:
    if any(
        (
            query,
            path_prefix,
            allowed_sources,
            allowed_schema_ids,
            allowed_content_states,
            writable is not None,
        )
    ):
        return
    raise ValueError("search_documents requires at least one query or filter")


def _normalize_optional_search_argument(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _matches_search_filters(
    document: ResolvedProjectDocumentCatalogRecord,
    *,
    path_prefix: str | None,
    allowed_sources: frozenset[str],
    allowed_schema_ids: frozenset[str],
    allowed_content_states: frozenset[ProjectDocumentContentState],
    writable: bool | None,
) -> bool:
    if path_prefix and not document.path.startswith(path_prefix):
        return False
    if writable is not None and document.writable is not writable:
        return False
    if allowed_sources and document.source not in allowed_sources:
        return False
    if allowed_schema_ids and document.schema_id not in allowed_schema_ids:
        return False
    if allowed_content_states and _resolve_visible_content_state(document) not in allowed_content_states:
        return False
    return True


def _build_search_hit(
    document: ResolvedProjectDocumentCatalogRecord,
    match: ProjectDocumentCatalogSearchMatch,
) -> ProjectDocumentSearchHitDTO:
    return ProjectDocumentSearchHitDTO(
        path=document.path,
        document_ref=document.document_ref,
        binding_version=_build_binding_version(document),
        resource_uri=document.resource_uri,
        title=document.title,
        source=document.source,
        document_kind=document.document_kind,
        schema_id=document.schema_id,
        content_state=_resolve_visible_content_state(document),
        writable=document.writable,
        version=document.version,
        updated_at=document.updated_at,
        matched_fields=list(match.matched_fields),
        match_score=match.match_score,
    )


def _resolve_catalog_search_match(
    document: ResolvedProjectDocumentCatalogRecord,
    normalized_query: str | None,
    query_terms: tuple[str, ...],
    intent_tags: frozenset[str],
) -> ProjectDocumentCatalogSearchMatch | None:
    if normalized_query is None and not intent_tags:
        return ProjectDocumentCatalogSearchMatch(matched_fields=(), match_score=0)
    matched_fields: list[ProjectDocumentSearchField] = []
    total_score = 0
    for field in PROJECT_DOCUMENT_SEARCH_FIELD_ORDER:
        value = _read_searchable_field_value(document, field)
        score = _score_search_field(
            value,
            normalized_query=normalized_query or "",
            query_terms=query_terms,
            base_weight=PROJECT_DOCUMENT_SEARCH_FIELD_WEIGHTS[field],
        )
        if score <= 0:
            continue
        matched_fields.append(field)
        total_score += score
    total_score += _score_search_intents(document, intent_tags=intent_tags)
    if not matched_fields and total_score <= 0:
        return None
    return ProjectDocumentCatalogSearchMatch(
        matched_fields=tuple(matched_fields),
        match_score=total_score,
    )


def _read_searchable_field_value(
    document: ResolvedProjectDocumentCatalogRecord,
    field: ProjectDocumentSearchField,
) -> str:
    value = {
        "path": document.path,
        "title": document.title,
        "schema_id": document.schema_id or "",
        "source": document.source,
        "document_kind": document.document_kind,
        "content_state": _resolve_visible_content_state(document),
    }[field]
    return _normalize_search_text(value) or ""


def _score_search_field(
    value: str,
    *,
    normalized_query: str,
    query_terms: tuple[str, ...],
    base_weight: int,
) -> int:
    if not value:
        return 0
    if value == normalized_query:
        return base_weight * 4
    if normalized_query and normalized_query in value:
        return base_weight * 3
    term_hits = sum(1 for term in query_terms if term in value)
    if term_hits == 0:
        return 0
    return base_weight + term_hits


def _normalize_search_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized


def _extract_search_terms(normalized_query: str | None) -> tuple[str, ...]:
    if normalized_query is None:
        return ()
    parts = [
        item
        for item in PROJECT_DOCUMENT_SEARCH_TERM_SEPARATOR.split(normalized_query)
        if item
    ]
    if not parts:
        return ()
    deduped = tuple(dict.fromkeys(parts))
    if normalized_query not in deduped:
        return (normalized_query, *deduped)
    return deduped


def _expand_search_terms(
    *,
    normalized_query: str | None,
    query_terms: tuple[str, ...],
) -> tuple[str, ...]:
    if normalized_query is None:
        return query_terms
    expanded = list(query_terms)
    for trigger, aliases in PROJECT_DOCUMENT_SEARCH_QUERY_EXPANSIONS.items():
        if _matches_query_keyword(normalized_query, query_terms, trigger):
            expanded.extend(aliases)
    return tuple(dict.fromkeys(expanded))


def _resolve_search_intent_tags(
    *,
    normalized_query: str | None,
    query_terms: tuple[str, ...],
) -> frozenset[str]:
    if normalized_query is None:
        return frozenset()
    return frozenset(
        intent
        for intent, keywords in PROJECT_DOCUMENT_SEARCH_QUERY_INTENT_KEYWORDS.items()
        if any(_matches_query_keyword(normalized_query, query_terms, keyword) for keyword in keywords)
    )


def _matches_query_keyword(
    normalized_query: str,
    query_terms: tuple[str, ...],
    keyword: str,
) -> bool:
    if keyword in normalized_query:
        return True
    return any(keyword in item for item in query_terms)


def _score_search_intents(
    document: ResolvedProjectDocumentCatalogRecord,
    *,
    intent_tags: frozenset[str],
) -> int:
    document_intents = PROJECT_DOCUMENT_SEARCH_PATH_INTENTS.get(document.path)
    if not document_intents or not intent_tags:
        return 0
    return sum(
        PROJECT_DOCUMENT_SEARCH_INTENT_WEIGHTS[intent]
        for intent in document_intents
        if intent in intent_tags
    )


def _sort_search_hits(hits: list[ProjectDocumentSearchHitDTO]) -> None:
    minimum = datetime.min.replace(tzinfo=UTC)
    hits.sort(key=lambda item: item.path)
    hits.sort(key=lambda item: item.updated_at or minimum, reverse=True)
    hits.sort(key=lambda item: item.match_score, reverse=True)
