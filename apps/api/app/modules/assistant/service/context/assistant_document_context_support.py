from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.service import (
    ProjectDocumentCapabilityService,
    ProjectDocumentCatalogEntryDTO,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from ..turn.assistant_turn_error_support import AssistantDocumentContextProjectionError
from ..dto import AssistantDocumentContextDTO, AssistantTurnRequestDTO


@dataclass(frozen=True)
class NormalizedAssistantTurnPayload:
    payload: AssistantTurnRequestDTO
    document_context_bindings: list[dict[str, Any]]


async def normalize_turn_payload(
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    project_document_capability_service: ProjectDocumentCapabilityService | None,
) -> NormalizedAssistantTurnPayload:
    if payload.document_context is None:
        return NormalizedAssistantTurnPayload(payload=payload, document_context_bindings=[])
    if project_id is None:
        raise BusinessRuleError("document_context 需要 project_id")
    if project_document_capability_service is None:
        raise ConfigurationError("Project document capability service is not configured")
    catalog = await project_document_capability_service.list_document_catalog(
        db,
        project_id,
        owner_id=owner_id,
    )
    active_entry = resolve_active_document_entry(payload.document_context, catalog)
    selected_entries = resolve_selected_document_entries(
        payload.document_context,
        catalog,
        active_document_ref=active_entry.document_ref if active_entry is not None else None,
    )
    catalog_version = resolve_document_context_catalog_version(
        payload.document_context,
        catalog,
        require_fresh_catalog_snapshot=require_fresh_catalog_snapshot(payload.document_context),
    )
    normalized_context = AssistantDocumentContextDTO(
        active_path=active_entry.path if active_entry is not None else payload.document_context.active_path,
        active_document_ref=(
            active_entry.document_ref
            if active_entry is not None
            else payload.document_context.active_document_ref
        ),
        active_binding_version=(
            active_entry.binding_version
            if active_entry is not None
            else payload.document_context.active_binding_version
        ),
        selected_paths=[item.path for item in selected_entries],
        selected_document_refs=[item.document_ref for item in selected_entries],
        active_buffer_state=payload.document_context.active_buffer_state,
        catalog_version=catalog_version,
    )
    return NormalizedAssistantTurnPayload(
        payload=payload.model_copy(update={"document_context": normalized_context}),
        document_context_bindings=build_document_context_bindings(
            normalized_context=normalized_context,
            active_entry=active_entry,
            selected_entries=selected_entries,
        ),
    )


def resolve_document_context_catalog_version(
    document_context: AssistantDocumentContextDTO,
    catalog: list[ProjectDocumentCatalogEntryDTO],
    *,
    require_fresh_catalog_snapshot: bool,
) -> str | None:
    catalog_version = catalog[0].catalog_version if catalog else None
    request_catalog_version = document_context.catalog_version
    if (
        require_fresh_catalog_snapshot
        and request_catalog_version is not None
        and catalog_version is not None
        and request_catalog_version != catalog_version
    ):
        raise AssistantDocumentContextProjectionError(
            "catalog_version_mismatch",
            "当前文稿目录已变化，请刷新文稿上下文后重试。",
        )
    return catalog_version or request_catalog_version


def require_fresh_catalog_snapshot(
    document_context: AssistantDocumentContextDTO,
) -> bool:
    if document_context.active_path and document_context.active_document_ref is None:
        return True
    if document_context.selected_paths and not document_context.selected_document_refs:
        return True
    if document_context.selected_paths and (
        len(document_context.selected_paths) != len(document_context.selected_document_refs)
    ):
        return True
    return False


def resolve_active_document_entry(
    document_context: AssistantDocumentContextDTO,
    catalog: list[ProjectDocumentCatalogEntryDTO],
) -> ProjectDocumentCatalogEntryDTO | None:
    entries_by_path = {item.path: item for item in catalog}
    entries_by_ref = {item.document_ref: item for item in catalog}
    if document_context.active_path:
        entry = entries_by_path.get(document_context.active_path)
        if entry is None:
            raise AssistantDocumentContextProjectionError(
                "active_document_not_found",
                "document_context.active_path 不存在于当前项目目录",
            )
        validate_active_document_projection(document_context, entry)
        return entry
    if document_context.active_document_ref:
        entry = entries_by_ref.get(document_context.active_document_ref)
        if entry is None:
            raise AssistantDocumentContextProjectionError(
                "active_document_not_found",
                "document_context.active_document_ref 不存在于当前项目目录",
            )
        validate_active_document_projection(document_context, entry)
        return entry
    if document_context.active_binding_version:
        raise AssistantDocumentContextProjectionError(
            "active_document_projection_invalid",
            "document_context.active_binding_version 缺少 active_path 或 active_document_ref",
        )
    return None


def resolve_selected_document_entries(
    document_context: AssistantDocumentContextDTO,
    catalog: list[ProjectDocumentCatalogEntryDTO],
    *,
    active_document_ref: str | None,
) -> list[ProjectDocumentCatalogEntryDTO]:
    entries_by_path = {item.path: item for item in catalog}
    entries_by_ref = {item.document_ref: item for item in catalog}
    if document_context.selected_paths and document_context.selected_document_refs:
        return resolve_selected_document_entry_pairs(
            document_context,
            entries_by_path,
            active_document_ref=active_document_ref,
        )
    if document_context.selected_paths:
        return resolve_selected_document_entries_by_path(
            document_context.selected_paths,
            entries_by_path,
            active_document_ref=active_document_ref,
        )
    if document_context.selected_document_refs:
        return resolve_selected_document_entries_by_ref(
            document_context.selected_document_refs,
            entries_by_ref,
            active_document_ref=active_document_ref,
        )
    return []


def resolve_selected_document_entry_pairs(
    document_context: AssistantDocumentContextDTO,
    entries_by_path: dict[str, ProjectDocumentCatalogEntryDTO],
    *,
    active_document_ref: str | None,
) -> list[ProjectDocumentCatalogEntryDTO]:
    if len(document_context.selected_paths) != len(document_context.selected_document_refs):
        raise AssistantDocumentContextProjectionError(
            "selected_document_projection_invalid",
            "document_context.selected_paths 与 selected_document_refs 数量不一致",
        )
    resolved: list[ProjectDocumentCatalogEntryDTO] = []
    seen_refs: set[str] = set()
    for path, document_ref in zip(
        document_context.selected_paths,
        document_context.selected_document_refs,
        strict=False,
    ):
        entry = require_selected_document_entry_by_path(entries_by_path, path)
        if entry.document_ref != document_ref:
            raise AssistantDocumentContextProjectionError(
                "selected_document_binding_mismatch",
                "附带文稿上下文已变化，请重新选择后重试。",
            )
        append_selected_document_entry(
            resolved,
            seen_refs,
            entry,
            active_document_ref=active_document_ref,
        )
    return resolved


def resolve_selected_document_entries_by_path(
    selected_paths: list[str],
    entries_by_path: dict[str, ProjectDocumentCatalogEntryDTO],
    *,
    active_document_ref: str | None,
) -> list[ProjectDocumentCatalogEntryDTO]:
    resolved: list[ProjectDocumentCatalogEntryDTO] = []
    seen_refs: set[str] = set()
    for path in selected_paths:
        entry = require_selected_document_entry_by_path(entries_by_path, path)
        append_selected_document_entry(
            resolved,
            seen_refs,
            entry,
            active_document_ref=active_document_ref,
        )
    return resolved


def resolve_selected_document_entries_by_ref(
    selected_document_refs: list[str],
    entries_by_ref: dict[str, ProjectDocumentCatalogEntryDTO],
    *,
    active_document_ref: str | None,
) -> list[ProjectDocumentCatalogEntryDTO]:
    resolved: list[ProjectDocumentCatalogEntryDTO] = []
    seen_refs: set[str] = set()
    for document_ref in selected_document_refs:
        entry = require_selected_document_entry_by_ref(entries_by_ref, document_ref)
        append_selected_document_entry(
            resolved,
            seen_refs,
            entry,
            active_document_ref=active_document_ref,
        )
    return resolved


def validate_active_document_projection(
    document_context: AssistantDocumentContextDTO,
    entry: ProjectDocumentCatalogEntryDTO,
) -> None:
    if (
        document_context.active_document_ref is not None
        and document_context.active_document_ref != entry.document_ref
    ):
        raise AssistantDocumentContextProjectionError(
            "active_document_binding_mismatch",
            "当前活动文稿绑定已变化，请刷新当前文稿后重试。",
        )
    if (
        document_context.active_binding_version is not None
        and document_context.active_binding_version != entry.binding_version
    ):
        raise AssistantDocumentContextProjectionError(
            "active_document_binding_mismatch",
            "当前活动文稿绑定已变化，请刷新当前文稿后重试。",
        )


def build_document_context_bindings(
    *,
    normalized_context: AssistantDocumentContextDTO,
    active_entry: ProjectDocumentCatalogEntryDTO | None,
    selected_entries: list[ProjectDocumentCatalogEntryDTO],
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    if active_entry is not None:
        active_buffer_state = normalized_context.active_buffer_state
        bindings.append(
            {
                "path": active_entry.path,
                "document_ref": active_entry.document_ref,
                "resource_uri": active_entry.resource_uri,
                "binding_version": active_entry.binding_version,
                "buffer_dirty": (
                    active_buffer_state.dirty
                    if active_buffer_state is not None
                    else None
                ),
                "base_version": (
                    active_buffer_state.base_version
                    if active_buffer_state is not None
                    else None
                ),
                "buffer_hash": (
                    active_buffer_state.buffer_hash
                    if active_buffer_state is not None
                    else None
                ),
                "buffer_source": (
                    active_buffer_state.source
                    if active_buffer_state is not None
                    else None
                ),
                "catalog_version": normalized_context.catalog_version,
                "selection_role": "active",
                "writable": active_entry.writable,
                "source": active_entry.source,
                "document_kind": active_entry.document_kind,
                "version": active_entry.version,
            }
        )
    for entry in selected_entries:
        bindings.append(
            {
                "path": entry.path,
                "document_ref": entry.document_ref,
                "resource_uri": entry.resource_uri,
                "binding_version": entry.binding_version,
                "buffer_dirty": None,
                "base_version": None,
                "buffer_hash": None,
                "buffer_source": None,
                "catalog_version": normalized_context.catalog_version,
                "selection_role": "selected",
                "writable": entry.writable,
                "source": entry.source,
                "document_kind": entry.document_kind,
                "version": entry.version,
            }
        )
    return bindings


def require_selected_document_entry_by_path(
    entries_by_path: dict[str, ProjectDocumentCatalogEntryDTO],
    path: str,
) -> ProjectDocumentCatalogEntryDTO:
    entry = entries_by_path.get(path)
    if entry is not None:
        return entry
    raise AssistantDocumentContextProjectionError(
        "selected_document_not_found",
        f"document_context.selected_paths 包含不存在文稿: {path}",
    )


def require_selected_document_entry_by_ref(
    entries_by_ref: dict[str, ProjectDocumentCatalogEntryDTO],
    document_ref: str,
) -> ProjectDocumentCatalogEntryDTO:
    entry = entries_by_ref.get(document_ref)
    if entry is not None:
        return entry
    raise AssistantDocumentContextProjectionError(
        "selected_document_not_found",
        f"document_context.selected_document_refs 包含不存在文稿: {document_ref}",
    )


def append_selected_document_entry(
    resolved: list[ProjectDocumentCatalogEntryDTO],
    seen_refs: set[str],
    entry: ProjectDocumentCatalogEntryDTO,
    *,
    active_document_ref: str | None,
) -> None:
    if entry.document_ref == active_document_ref or entry.document_ref in seen_refs:
        return
    resolved.append(entry)
    seen_refs.add(entry.document_ref)
