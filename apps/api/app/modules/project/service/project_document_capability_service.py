from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import TYPE_CHECKING, Literal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.infrastructure import ProjectDocumentRevisionRecord, ProjectDocumentRevisionStore
from app.shared.runtime.errors import BusinessRuleError

from .project_document_capability_dto import (
    ProjectDocumentCatalogEntryDTO,
    ProjectDocumentContentState,
    ProjectDocumentReadErrorDTO,
    ProjectDocumentReadItemDTO,
    ProjectDocumentReadResultDTO,
    ProjectDocumentSearchResultDTO,
    ProjectDocumentWriteDiffSummaryDTO,
    ProjectDocumentWriteResultDTO,
)
from .project_document_catalog_support import (
    DEFAULT_CHAPTER_PATH_TEMPLATE,
    MARKDOWN_MIME_TYPE,
    PROJECT_DOCUMENT_SCHEMA_IDS,
    ResolvedProjectDocument,
    ResolvedProjectDocumentCatalogRecord,
    _build_binding_version,
    _build_catalog_version,
    _build_content_hash,
    _build_read_projection,
    _build_resource_uri,
    _flatten_tree_file_paths,
    _pair_paths_and_cursors,
    _resolve_catalog_content_state,
    _resolve_content_state,
    _resolve_document_kind,
    _resolve_mime_type,
    _resolve_title,
    _to_catalog_entry,
)
from .project_document_search_support import (
    PROJECT_DOCUMENT_SEARCH_DEFAULT_LIMIT,
    _build_search_hit,
    _expand_search_terms,
    _extract_search_terms,
    _matches_search_filters,
    _normalize_optional_search_argument,
    _normalize_search_text,
    _resolve_catalog_search_match,
    _resolve_search_intent_tags,
    _sort_search_hits,
    _validate_search_limit,
    _validate_search_request,
)
from .project_document_support import (
    OPENING_PLAN_DOCUMENT_PATH,
    OUTLINE_DOCUMENT_PATH,
    is_canonical_project_document_path,
    is_mutable_project_document_file_path,
    parse_chapter_number_from_document_path,
)
from .project_document_schema_support import (
    ProjectDocumentSchemaValidationError,
    validate_project_document_schema,
)
from .project_document_version_support import (
    build_project_canonical_document_version,
    build_project_file_document_version,
)
from .project_service import ProjectService

if TYPE_CHECKING:
    from app.modules.content.service import (
        CanonicalProjectDocumentDTO,
        CanonicalProjectDocumentQueryService,
    )
    from app.modules.project.infrastructure import (
        ProjectDocumentFileStore,
        ProjectDocumentIdentityStore,
    )


@dataclass(frozen=True)
class PreparedProjectDocumentWrite:
    project_id: uuid.UUID
    path: str
    content: str
    owner_id: uuid.UUID | None
    resolved_document: ResolvedProjectDocument
    run_audit_id: str
    effective_write_state: Literal["write_pending", "revision_recovery", "already_committed"] = "write_pending"
    revision_record: ProjectDocumentRevisionRecord | None = None


class ProjectDocumentMutationError(BusinessRuleError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ProjectDocumentCommittedMutationError(ProjectDocumentMutationError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.write_effective = True
        self.terminal_status = "failed"
        self.effective_status = "committed"


def _build_project_document_write_result(
    *,
    resolved_document: ResolvedProjectDocument,
    content: str,
    updated_at: datetime | None,
    revision_record: ProjectDocumentRevisionRecord,
    changed: bool,
) -> ProjectDocumentWriteResultDTO:
    return ProjectDocumentWriteResultDTO(
        path=resolved_document.path,
        document_ref=resolved_document.document_ref,
        resource_uri=resolved_document.resource_uri,
        source="file",
        version=revision_record.version,
        document_revision_id=revision_record.document_revision_id,
        updated_at=updated_at or datetime.now(UTC),
        diff_summary=ProjectDocumentWriteDiffSummaryDTO(
            changed=changed,
            previous_chars=len(resolved_document.content),
            next_chars=len(content),
        ),
        run_audit_id=revision_record.run_audit_id,
    )


class ProjectDocumentCapabilityService:
    def __init__(
        self,
        *,
        project_service: ProjectService,
        document_file_store: "ProjectDocumentFileStore | None" = None,
        document_identity_store: "ProjectDocumentIdentityStore | None" = None,
        document_revision_store: ProjectDocumentRevisionStore | None = None,
        canonical_document_query_service: "CanonicalProjectDocumentQueryService | None" = None,
    ) -> None:
        self.project_service = project_service
        self.document_file_store = document_file_store or project_service.document_file_store
        self.document_identity_store = document_identity_store or project_service.document_identity_store
        self.document_revision_store = document_revision_store or (
            ProjectDocumentRevisionStore(self.document_file_store.root)
            if self.document_file_store is not None
            else None
        )
        if canonical_document_query_service is None:
            from app.modules.content.service import create_canonical_project_document_query_service

            canonical_document_query_service = create_canonical_project_document_query_service(
                project_service=project_service,
            )
        self.canonical_document_query_service = canonical_document_query_service

    async def list_document_catalog(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[ProjectDocumentCatalogEntryDTO]:
        documents = await self._resolve_catalog_documents(db, project_id, owner_id=owner_id)
        catalog_version = _build_catalog_version(documents.values())
        return [
            _to_catalog_entry(document, catalog_version=catalog_version)
            for document in documents.values()
        ]

    async def read_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        paths: Iterable[str],
        cursors: Iterable[str] | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentReadResultDTO:
        requested_paths = list(paths)
        requested_cursors = list(cursors or [])
        catalog_documents = await self._resolve_catalog_documents(db, project_id, owner_id=owner_id)
        documents = await self._resolve_documents_by_paths(
            db,
            project_id,
            paths=requested_paths,
            owner_id=owner_id,
        )
        catalog_version = _build_catalog_version(catalog_documents.values())
        items: list[ProjectDocumentReadItemDTO] = []
        errors: list[ProjectDocumentReadErrorDTO] = []
        cursor_by_path = _pair_paths_and_cursors(requested_paths, requested_cursors)
        for path in requested_paths:
            resolved = documents.get(path)
            if resolved is None:
                errors.append(
                    ProjectDocumentReadErrorDTO(
                        path=path,
                        code="document_not_found",
                        message="目标文稿不存在于当前项目目录",
                    )
                )
                continue
            cursor = cursor_by_path.get(path)
            read_item, read_error = _build_read_projection(
                resolved,
                catalog_version=catalog_version,
                cursor=cursor,
            )
            if read_error is not None:
                errors.append(read_error)
                continue
            items.append(read_item)
        return ProjectDocumentReadResultDTO(
            documents=items,
            errors=errors,
            catalog_version=catalog_version,
        )

    async def search_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        query: str | None = None,
        path_prefix: str | None = None,
        sources: Iterable[str] = (),
        schema_ids: Iterable[str] = (),
        content_states: Iterable[ProjectDocumentContentState] = (),
        writable: bool | None = None,
        limit: int = PROJECT_DOCUMENT_SEARCH_DEFAULT_LIMIT,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentSearchResultDTO:
        _validate_search_limit(limit)
        normalized_query_input = _normalize_optional_search_argument(query, field_name="query")
        normalized_path_prefix = _normalize_optional_search_argument(
            path_prefix,
            field_name="path_prefix",
        )
        catalog_documents = await self._resolve_catalog_documents(db, project_id, owner_id=owner_id)
        catalog_version = _build_catalog_version(catalog_documents.values())
        normalized_query = _normalize_search_text(normalized_query_input)
        query_terms = _expand_search_terms(
            normalized_query=normalized_query,
            query_terms=_extract_search_terms(normalized_query),
        )
        intent_tags = _resolve_search_intent_tags(
            normalized_query=normalized_query,
            query_terms=query_terms,
        )
        allowed_sources = frozenset(item for item in sources if item)
        allowed_schema_ids = frozenset(item for item in schema_ids if item)
        allowed_content_states = frozenset(item for item in content_states if item)
        _validate_search_request(
            query=normalized_query,
            path_prefix=normalized_path_prefix,
            allowed_sources=allowed_sources,
            allowed_schema_ids=allowed_schema_ids,
            allowed_content_states=allowed_content_states,
            writable=writable,
        )
        hits = [
            _build_search_hit(document, match)
            for document in catalog_documents.values()
            if _matches_search_filters(
                document,
                path_prefix=normalized_path_prefix,
                allowed_sources=allowed_sources,
                allowed_schema_ids=allowed_schema_ids,
                allowed_content_states=allowed_content_states,
                writable=writable,
            )
            and (
                match := _resolve_catalog_search_match(
                    document,
                    normalized_query=normalized_query,
                    query_terms=query_terms,
                    intent_tags=intent_tags,
                )
            )
            is not None
        ]
        _sort_search_hits(hits)
        return ProjectDocumentSearchResultDTO(
            documents=hits[:limit],
            catalog_version=catalog_version,
        )

    async def write_document(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        path: str,
        content: str,
        base_version: str,
        owner_id: uuid.UUID | None = None,
        expected_document_ref: str | None = None,
        expected_binding_version: str | None = None,
        active_buffer_state: dict[str, object] | None = None,
        allowed_target_document_refs: tuple[str, ...] = (),
        require_trusted_buffer_state: bool = False,
        run_audit_id: str,
    ) -> ProjectDocumentWriteResultDTO:
        prepared = await self.prepare_write_document(
            db,
            project_id,
            path=path,
            content=content,
            base_version=base_version,
            owner_id=owner_id,
            expected_document_ref=expected_document_ref,
            expected_binding_version=expected_binding_version,
            active_buffer_state=active_buffer_state,
            allowed_target_document_refs=allowed_target_document_refs,
            require_trusted_buffer_state=require_trusted_buffer_state,
            run_audit_id=run_audit_id,
        )
        return await self.commit_prepared_write_document(db, prepared)

    async def prepare_write_document(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        path: str,
        content: str,
        base_version: str,
        owner_id: uuid.UUID | None = None,
        expected_document_ref: str | None = None,
        expected_binding_version: str | None = None,
        active_buffer_state: dict[str, object] | None = None,
        allowed_target_document_refs: tuple[str, ...] = (),
        require_trusted_buffer_state: bool = False,
        run_audit_id: str,
    ) -> PreparedProjectDocumentWrite:
        resolved = await self._resolve_document_by_path(
            db,
            project_id,
            path=path,
            owner_id=owner_id,
        )
        if resolved is None:
            raise ProjectDocumentMutationError(
                "document_not_found",
                "目标文稿不存在于当前项目目录，无法写回。",
            )
        if not resolved.writable:
            raise ProjectDocumentMutationError(
                "document_not_writable",
                "目标文稿当前不可写，请改为更新项目文件层文稿。",
            )
        if allowed_target_document_refs and resolved.document_ref not in allowed_target_document_refs:
            raise ProjectDocumentMutationError(
                "write_target_not_allowed",
                "目标文稿不在当前 turn 的写入授权范围内。",
            )
        if expected_document_ref is not None and resolved.document_ref != expected_document_ref:
            raise ProjectDocumentMutationError(
                "write_target_mismatch",
                "目标文稿身份与当前写入授权不一致。",
            )
        desired_content_hash = _build_content_hash(content)
        desired_version = build_project_file_document_version(content)
        current_content_hash = _build_content_hash(resolved.content)
        binding_version = _build_binding_version(resolved)
        if expected_binding_version is not None and binding_version != expected_binding_version:
            raise ProjectDocumentMutationError(
                "binding_version_mismatch",
                "目标文稿绑定已变化，请重新读取当前上下文后再尝试写入。",
            )
        existing_revision = self._get_revision_by_run_audit_id(
            project_id,
            document_ref=resolved.document_ref,
            run_audit_id=run_audit_id,
        )
        if existing_revision is not None:
            if existing_revision.version != desired_version or existing_revision.content_hash != desired_content_hash:
                raise ProjectDocumentMutationError(
                    "run_audit_conflict",
                    "同一个 run_audit_id 不能复用到不同文稿内容。",
                )
            if existing_revision.version != resolved.version or existing_revision.content_hash != current_content_hash:
                raise ProjectDocumentMutationError(
                    "revision_state_mismatch",
                    "当前文稿内容与既有 revision 锚点不一致，请先重新读取最新状态。",
                )
            _validate_active_buffer_state(
                active_buffer_state,
                base_version=base_version,
                current_content=resolved.content,
                require_trusted_snapshot=require_trusted_buffer_state,
            )
            _validate_document_content(content, schema_id=resolved.schema_id, path=resolved.path)
            return PreparedProjectDocumentWrite(
                project_id=project_id,
                path=path,
                content=content,
                owner_id=owner_id,
                resolved_document=resolved,
                run_audit_id=run_audit_id,
                effective_write_state="already_committed",
                revision_record=existing_revision,
            )
        if resolved.version != base_version:
            if resolved.version == desired_version and current_content_hash == desired_content_hash:
                _validate_active_buffer_state(
                    active_buffer_state,
                    base_version=base_version,
                    current_content=resolved.content,
                    require_trusted_snapshot=require_trusted_buffer_state,
                )
                _validate_document_content(content, schema_id=resolved.schema_id, path=resolved.path)
                return PreparedProjectDocumentWrite(
                    project_id=project_id,
                    path=path,
                    content=content,
                    owner_id=owner_id,
                    resolved_document=resolved,
                    run_audit_id=run_audit_id,
                    effective_write_state="revision_recovery",
                )
            raise ProjectDocumentMutationError(
                "version_conflict",
                "目标文稿版本已变化，请重新读取最新内容后再写入。",
            )
        revision_state = self._resolve_revision_state(project_id, resolved)
        if revision_state == "mismatch":
            if resolved.version == desired_version and current_content_hash == desired_content_hash:
                _validate_active_buffer_state(
                    active_buffer_state,
                    base_version=base_version,
                    current_content=resolved.content,
                    require_trusted_snapshot=require_trusted_buffer_state,
                )
                _validate_document_content(content, schema_id=resolved.schema_id, path=resolved.path)
                return PreparedProjectDocumentWrite(
                    project_id=project_id,
                    path=path,
                    content=content,
                    owner_id=owner_id,
                    resolved_document=resolved,
                    run_audit_id=run_audit_id,
                    effective_write_state="revision_recovery",
                )
            raise ProjectDocumentMutationError(
                "revision_state_mismatch",
                "当前文稿内容与 revision 元数据不一致，请先重新读取最新状态。",
            )
        _validate_active_buffer_state(
            active_buffer_state,
            base_version=base_version,
            current_content=resolved.content,
            require_trusted_snapshot=require_trusted_buffer_state,
        )
        _validate_document_content(content, schema_id=resolved.schema_id, path=resolved.path)
        return PreparedProjectDocumentWrite(
            project_id=project_id,
            path=path,
            content=content,
            owner_id=owner_id,
            resolved_document=resolved,
            run_audit_id=run_audit_id,
        )

    async def commit_prepared_write_document(
        self,
        db: AsyncSession,
        prepared: PreparedProjectDocumentWrite,
    ) -> ProjectDocumentWriteResultDTO:
        resolved = prepared.resolved_document
        if prepared.effective_write_state == "already_committed":
            if prepared.revision_record is None:
                raise RuntimeError("Prepared project document write is missing revision_record")
            return _build_project_document_write_result(
                resolved_document=resolved,
                content=resolved.content,
                updated_at=resolved.updated_at,
                revision_record=prepared.revision_record,
                changed=False,
            )
        saved_content = resolved.content
        saved_updated_at = resolved.updated_at
        changed = False
        revision_store = self._require_revision_store()
        file_store = self.document_file_store
        if file_store is None:
            raise RuntimeError("Project document file store is not configured")
        with revision_store.revision_lock(prepared.project_id):
            if prepared.effective_write_state == "write_pending":
                with file_store.project_document_tree_lock(prepared.project_id):
                    saved = file_store.save_project_document(
                        prepared.project_id,
                        prepared.path,
                        prepared.content,
                        expected_version=resolved.version,
                    )
                    saved_content = saved.content
                    saved_updated_at = saved.updated_at
                    changed = resolved.content != saved.content
            next_content_hash = _build_content_hash(saved_content)
            next_version = build_project_file_document_version(saved_content)
            try:
                revision_record = revision_store.append_revision_unlocked(
                    prepared.project_id,
                    document_ref=resolved.document_ref,
                    content_hash=next_content_hash,
                    version=next_version,
                    run_audit_id=prepared.run_audit_id,
                )
            except Exception as exc:
                detail = str(exc).strip()
                message = "文稿内容已写入，但 revision 元数据未能落盘。请刷新当前文稿确认最新内容。"
                if detail:
                    message = f"{message} 底层错误：{detail}"
                raise ProjectDocumentCommittedMutationError(
                    "document_revision_persist_failed",
                    message,
                ) from exc
        return _build_project_document_write_result(
            resolved_document=resolved,
            content=saved_content,
            updated_at=saved_updated_at,
            revision_record=revision_record,
            changed=changed,
        )

    def _resolve_revision_state(
        self,
        project_id: uuid.UUID,
        document: ResolvedProjectDocument,
    ) -> Literal["empty", "consistent", "mismatch"]:
        revision_store = self._require_revision_store()
        latest_revision = revision_store.get_latest_revision(
            project_id,
            document_ref=document.document_ref,
        )
        if latest_revision is None:
            return "empty"
        current_content_hash = _build_content_hash(document.content)
        if (
            latest_revision.version != document.version
            or latest_revision.content_hash != current_content_hash
        ):
            return "mismatch"
        return "consistent"

    def _append_revision(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str,
        content_hash: str,
        version: str,
        run_audit_id: str,
    ):
        return self._require_revision_store().append_revision(
            project_id,
            document_ref=document_ref,
            content_hash=content_hash,
            version=version,
            run_audit_id=run_audit_id,
        )

    def _get_revision_by_run_audit_id(
        self,
        project_id: uuid.UUID,
        *,
        document_ref: str,
        run_audit_id: str,
    ) -> ProjectDocumentRevisionRecord | None:
        return self._require_revision_store().get_revision_by_run_audit_id(
            project_id,
            document_ref=document_ref,
            run_audit_id=run_audit_id,
        )

    def _require_revision_store(self) -> ProjectDocumentRevisionStore:
        if self.document_revision_store is None:
            raise RuntimeError("Project document revision store is not configured")
        return self.document_revision_store

    async def _resolve_catalog_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> dict[str, ResolvedProjectDocumentCatalogRecord]:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        canonical_documents = await self._list_canonical_documents(
            db,
            project.id,
            include_content=False,
        )
        chapter_paths, file_paths = self._collect_file_layer_paths(project.id)
        resolved_documents = self._build_file_catalog_documents(project.id, file_paths)
        resolved_documents.update(
            self._build_canonical_catalog_documents(project.id, canonical_documents, chapter_paths)
        )
        return dict(sorted(resolved_documents.items(), key=lambda item: item[0]))

    async def _resolve_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> dict[str, ResolvedProjectDocument]:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        canonical_documents = await self._list_canonical_documents(
            db,
            project.id,
            include_content=True,
        )
        chapter_paths, file_paths = self._collect_file_layer_paths(project.id)
        resolved_documents = self._build_file_documents(project.id, file_paths)
        resolved_documents.update(
            self._build_canonical_documents(project.id, canonical_documents, chapter_paths)
        )
        return dict(sorted(resolved_documents.items(), key=lambda item: item[0]))

    async def _resolve_documents_by_paths(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        paths: Iterable[str],
        owner_id: uuid.UUID | None = None,
    ) -> dict[str, ResolvedProjectDocument]:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        requested_paths = tuple(dict.fromkeys(paths))
        return await self._build_requested_documents(db, project.id, requested_paths)

    async def _resolve_document_by_path(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        path: str,
        owner_id: uuid.UUID | None = None,
    ) -> ResolvedProjectDocument | None:
        documents = await self._resolve_documents_by_paths(
            db,
            project_id,
            paths=(path,),
            owner_id=owner_id,
        )
        return documents.get(path)

    async def _list_canonical_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        include_content: bool,
    ) -> list["CanonicalProjectDocumentDTO"]:
        return await self.canonical_document_query_service.list_canonical_documents(
            db,
            project_id,
            include_content=include_content,
        )

    async def _list_selected_canonical_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        include_content: bool,
        include_outline: bool = False,
        include_opening_plan: bool = False,
        chapter_numbers: Iterable[int] = (),
    ) -> list["CanonicalProjectDocumentDTO"]:
        return await self.canonical_document_query_service.list_selected_canonical_documents(
            db,
            project_id,
            include_content=include_content,
            include_outline=include_outline,
            include_opening_plan=include_opening_plan,
            chapter_numbers=chapter_numbers,
        )

    def _collect_file_layer_paths(
        self,
        project_id: uuid.UUID,
    ) -> tuple[dict[int, str], list[str]]:
        if self.document_file_store is None:
            return {}, []
        chapter_paths: dict[int, str] = {}
        file_paths: list[str] = []
        for path in _flatten_tree_file_paths(self.document_file_store.list_project_document_tree(project_id)):
            if path in {OUTLINE_DOCUMENT_PATH, OPENING_PLAN_DOCUMENT_PATH}:
                continue
            chapter_number = parse_chapter_number_from_document_path(path)
            if chapter_number is not None:
                chapter_paths[chapter_number] = path
                continue
            file_paths.append(path)
        return chapter_paths, file_paths

    async def _build_requested_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        requested_paths: tuple[str, ...],
    ) -> dict[str, ResolvedProjectDocument]:
        if not requested_paths:
            return {}
        canonical_paths = tuple(
            path for path in requested_paths if is_canonical_project_document_path(path)
        )
        file_paths = tuple(
            path for path in requested_paths if not is_canonical_project_document_path(path)
        )
        documents: dict[str, ResolvedProjectDocument] = {}
        if file_paths:
            documents.update(self._build_requested_file_documents(project_id, file_paths))
        if canonical_paths:
            documents.update(
                await self._build_requested_canonical_documents(
                    db,
                    project_id,
                    canonical_paths,
                )
            )
        return dict(sorted(documents.items(), key=lambda item: item[0]))

    def _build_requested_file_documents(
        self,
        project_id: uuid.UUID,
        file_paths: tuple[str, ...],
    ) -> dict[str, ResolvedProjectDocument]:
        if self.document_file_store is None:
            return {}
        documents: dict[str, ResolvedProjectDocument] = {}
        for path in sorted(file_paths):
            record = self.document_file_store.find_project_document(project_id, path)
            if record is None:
                continue
            document_ref = self._resolve_file_document_ref(project_id, path=path)
            documents[path] = ResolvedProjectDocument(
                content=record.content,
                content_state=_resolve_content_state(record.content),
                document_kind=_resolve_document_kind(path, source="file"),
                document_ref=document_ref,
                mime_type=_resolve_mime_type(path),
                path=path,
                resource_uri=_build_resource_uri(project_id, document_ref),
                schema_id=PROJECT_DOCUMENT_SCHEMA_IDS.get(path),
                source="file",
                title=_resolve_title(path),
                updated_at=record.updated_at,
                version=build_project_file_document_version(record.content),
                writable=is_mutable_project_document_file_path(path),
                readable=True,
            )
        return documents

    async def _build_requested_canonical_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        canonical_paths: tuple[str, ...],
    ) -> dict[str, ResolvedProjectDocument]:
        include_outline = OUTLINE_DOCUMENT_PATH in canonical_paths
        include_opening_plan = OPENING_PLAN_DOCUMENT_PATH in canonical_paths
        requested_chapter_paths = {
            path: chapter_number
            for path in canonical_paths
            if (chapter_number := parse_chapter_number_from_document_path(path)) is not None
        }
        valid_chapter_paths = self._resolve_requested_chapter_paths(
            project_id,
            requested_chapter_paths,
        )
        selected_documents = await self._list_selected_canonical_documents(
            db,
            project_id,
            include_content=True,
            include_outline=include_outline,
            include_opening_plan=include_opening_plan,
            chapter_numbers=tuple(valid_chapter_paths.keys()),
        )
        content_by_type = {
            item.content_type: item
            for item in selected_documents
            if item.content_type in {"outline", "opening_plan"}
        }
        content_by_chapter = {
            item.chapter_number: item
            for item in selected_documents
            if item.content_type == "chapter" and item.chapter_number is not None
        }
        resolved: dict[str, ResolvedProjectDocument] = {}
        if include_outline:
            resolved[OUTLINE_DOCUMENT_PATH] = self._build_canonical_document(
                project_id,
                path=OUTLINE_DOCUMENT_PATH,
                content=content_by_type.get("outline"),
                document_ref="canonical:outline",
                source="outline",
            )
        if include_opening_plan:
            resolved[OPENING_PLAN_DOCUMENT_PATH] = self._build_canonical_document(
                project_id,
                path=OPENING_PLAN_DOCUMENT_PATH,
                content=content_by_type.get("opening_plan"),
                document_ref="canonical:opening_plan",
                source="opening_plan",
            )
        for chapter_number, path in valid_chapter_paths.items():
            document = content_by_chapter.get(chapter_number)
            if document is None:
                continue
            resolved[path] = self._build_canonical_document(
                project_id,
                path=path,
                content=document,
                document_ref=f"canonical:chapter:{chapter_number:03d}",
                source="chapter",
            )
        return resolved

    def _resolve_requested_chapter_paths(
        self,
        project_id: uuid.UUID,
        requested_chapter_paths: dict[str, int],
    ) -> dict[int, str]:
        if not requested_chapter_paths:
            return {}
        chapter_paths, _ = self._collect_file_layer_paths(project_id)
        valid_paths: dict[int, str] = {}
        for path, chapter_number in requested_chapter_paths.items():
            resolved_path = chapter_paths.get(
                chapter_number,
                DEFAULT_CHAPTER_PATH_TEMPLATE.format(chapter_number=chapter_number),
            )
            if resolved_path != path:
                continue
            valid_paths[chapter_number] = path
        return valid_paths

    def _build_file_documents(
        self,
        project_id: uuid.UUID,
        file_paths: list[str],
    ) -> dict[str, ResolvedProjectDocument]:
        if self.document_file_store is None:
            return {}
        documents: dict[str, ResolvedProjectDocument] = {}
        for path in sorted(file_paths):
            record = self.document_file_store.find_project_document(project_id, path)
            if record is None:
                continue
            document_ref = self._resolve_file_document_ref(project_id, path=path)
            documents[path] = ResolvedProjectDocument(
                content=record.content,
                content_state=_resolve_content_state(record.content),
                document_kind=_resolve_document_kind(path, source="file"),
                document_ref=document_ref,
                mime_type=_resolve_mime_type(path),
                path=path,
                resource_uri=_build_resource_uri(project_id, document_ref),
                schema_id=PROJECT_DOCUMENT_SCHEMA_IDS.get(path),
                source="file",
                title=_resolve_title(path),
                updated_at=record.updated_at,
                version=build_project_file_document_version(record.content),
                writable=is_mutable_project_document_file_path(path),
                readable=True,
            )
        return documents

    def _build_file_catalog_documents(
        self,
        project_id: uuid.UUID,
        file_paths: list[str],
    ) -> dict[str, ResolvedProjectDocumentCatalogRecord]:
        if self.document_file_store is None:
            return {}
        documents: dict[str, ResolvedProjectDocumentCatalogRecord] = {}
        for path in sorted(file_paths):
            record = self.document_file_store.find_project_document_metadata(project_id, path)
            if record is None:
                continue
            document_ref = self._resolve_file_document_ref(project_id, path=path)
            documents[path] = ResolvedProjectDocumentCatalogRecord(
                content_state="ready" if record.size_bytes > 0 else "empty",
                document_kind=_resolve_document_kind(path, source="file"),
                document_ref=document_ref,
                mime_type=_resolve_mime_type(path),
                path=path,
                resource_uri=_build_resource_uri(project_id, document_ref),
                schema_id=PROJECT_DOCUMENT_SCHEMA_IDS.get(path),
                source="file",
                title=_resolve_title(path),
                updated_at=record.updated_at,
                version=f"sha256:{record.content_hash}",
                writable=is_mutable_project_document_file_path(path),
                readable=True,
            )
        return documents

    def _build_canonical_documents(
        self,
        project_id: uuid.UUID,
        documents: list["CanonicalProjectDocumentDTO"],
        chapter_paths: dict[int, str],
    ) -> dict[str, ResolvedProjectDocument]:
        content_by_type = {
            item.content_type: item
            for item in documents
            if item.content_type in {"outline", "opening_plan"}
        }
        chapter_contents = sorted(
            (
                item
                for item in documents
                if item.content_type == "chapter" and item.chapter_number is not None
            ),
            key=lambda item: item.chapter_number or 0,
        )
        resolved = {
            OUTLINE_DOCUMENT_PATH: self._build_canonical_document(
                project_id,
                path=OUTLINE_DOCUMENT_PATH,
                content=content_by_type.get("outline"),
                document_ref="canonical:outline",
                source="outline",
            ),
            OPENING_PLAN_DOCUMENT_PATH: self._build_canonical_document(
                project_id,
                path=OPENING_PLAN_DOCUMENT_PATH,
                content=content_by_type.get("opening_plan"),
                document_ref="canonical:opening_plan",
                source="opening_plan",
            ),
        }
        for item in chapter_contents:
            chapter_number = item.chapter_number
            if chapter_number is None:
                continue
            path = chapter_paths.get(chapter_number, DEFAULT_CHAPTER_PATH_TEMPLATE.format(chapter_number=chapter_number))
            resolved[path] = self._build_canonical_document(
                project_id,
                path=path,
                content=item,
                document_ref=f"canonical:chapter:{chapter_number:03d}",
                source="chapter",
            )
        return resolved

    def _build_canonical_catalog_documents(
        self,
        project_id: uuid.UUID,
        documents: list["CanonicalProjectDocumentDTO"],
        chapter_paths: dict[int, str],
    ) -> dict[str, ResolvedProjectDocumentCatalogRecord]:
        row_by_type = {
            item.content_type: item
            for item in documents
            if item.content_type in {"outline", "opening_plan"}
        }
        chapter_rows = sorted(
            (
                item
                for item in documents
                if item.content_type == "chapter" and item.chapter_number is not None
            ),
            key=lambda item: item.chapter_number or 0,
        )
        resolved = {
            OUTLINE_DOCUMENT_PATH: self._build_canonical_catalog_document(
                project_id,
                path=OUTLINE_DOCUMENT_PATH,
                row=row_by_type.get("outline"),
                document_ref="canonical:outline",
                source="outline",
            ),
            OPENING_PLAN_DOCUMENT_PATH: self._build_canonical_catalog_document(
                project_id,
                path=OPENING_PLAN_DOCUMENT_PATH,
                row=row_by_type.get("opening_plan"),
                document_ref="canonical:opening_plan",
                source="opening_plan",
            ),
        }
        for item in chapter_rows:
            chapter_number = item.chapter_number
            if chapter_number is None:
                continue
            path = chapter_paths.get(
                chapter_number,
                DEFAULT_CHAPTER_PATH_TEMPLATE.format(chapter_number=chapter_number),
            )
            resolved[path] = self._build_canonical_catalog_document(
                project_id,
                path=path,
                row=item,
                document_ref=f"canonical:chapter:{chapter_number:03d}",
                source="chapter",
            )
        return resolved

    def _build_canonical_document(
        self,
        project_id: uuid.UUID,
        *,
        path: str,
        content: "CanonicalProjectDocumentDTO | None",
        document_ref: str,
        source: str,
    ) -> ResolvedProjectDocument:
        content_text = "" if content is None else content.content_text
        return ResolvedProjectDocument(
            content=content_text,
            content_state=_resolve_content_state(content_text),
            document_kind=source if content is None else content.content_type,
            document_ref=document_ref,
            mime_type=MARKDOWN_MIME_TYPE,
            path=path,
            resource_uri=_build_resource_uri(project_id, document_ref),
            schema_id=None,
            source=source,
            title=_resolve_title(path) if content is None else content.title,
            updated_at=None if content is None else content.updated_at,
            version=build_project_canonical_document_version(
                document_ref,
                content_id=None if content is None else content.content_id,
                version_number=None if content is None else content.version_number,
            ),
            writable=False,
            readable=content is not None and content.version_number is not None,
        )

    def _build_canonical_catalog_document(
        self,
        project_id: uuid.UUID,
        *,
        path: str,
        row: "CanonicalProjectDocumentDTO | None",
        document_ref: str,
        source: str,
    ) -> ResolvedProjectDocumentCatalogRecord:
        version_number = None if row is None else row.version_number
        return ResolvedProjectDocumentCatalogRecord(
            content_state=_resolve_catalog_content_state(
                version_number=version_number,
                word_count=None if row is None else row.word_count,
            ),
            document_kind=source if row is None else row.content_type,
            document_ref=document_ref,
            mime_type=MARKDOWN_MIME_TYPE,
            path=path,
            resource_uri=_build_resource_uri(project_id, document_ref),
            schema_id=None,
            source=source,
            title=_resolve_title(path) if row is None else row.title,
            updated_at=None if row is None else row.updated_at,
            version=build_project_canonical_document_version(
                document_ref,
                content_id=None if row is None else row.content_id,
                version_number=version_number,
            ),
            writable=False,
            readable=row is not None and version_number is not None,
        )

    def _resolve_file_document_ref(
        self,
        project_id: uuid.UUID,
        *,
        path: str,
    ) -> str:
        return self._require_document_identity_store().resolve_document_ref(project_id, path=path)

    def _require_document_identity_store(self) -> "ProjectDocumentIdentityStore":
        if self.document_identity_store is None:
            raise RuntimeError("Project document identity store is not configured")
        return self.document_identity_store

def _validate_active_buffer_state(
    active_buffer_state: dict[str, object] | None,
    *,
    base_version: str,
    current_content: str,
    require_trusted_snapshot: bool = False,
) -> None:
    if not isinstance(active_buffer_state, dict):
        if require_trusted_snapshot:
            raise ProjectDocumentMutationError(
                "active_buffer_state_required",
                "当前活动文稿缺少可信缓冲区快照，暂不能写回。",
            )
        return
    dirty = active_buffer_state.get("dirty")
    if not isinstance(dirty, bool):
        raise ProjectDocumentMutationError(
            "active_buffer_state_invalid",
            "当前活动文稿缓冲区快照无效，暂不能写回。",
        )
    buffer_base_version = active_buffer_state.get("base_version")
    if not isinstance(buffer_base_version, str) or not buffer_base_version.strip():
        if require_trusted_snapshot:
            raise ProjectDocumentMutationError(
                "active_buffer_state_required",
                "当前活动文稿缺少可信缓冲区快照，暂不能写回。",
            )
        return
    if dirty:
        raise ProjectDocumentMutationError(
            "dirty_buffer_conflict",
            "当前活跃缓冲区仍有未保存更改，请先保存或放弃后再重试。",
        )
    if buffer_base_version != base_version:
        raise ProjectDocumentMutationError(
            "write_grant_expired",
            "当前写回授权基线已变化，请重新读取当前文稿后再尝试写入。",
        )
    buffer_hash = active_buffer_state.get("buffer_hash")
    if buffer_hash is None:
        return
    if not isinstance(buffer_hash, str) or not buffer_hash.strip():
        raise ProjectDocumentMutationError(
            "active_buffer_state_invalid",
            "当前活动文稿缓冲区快照无效，暂不能写回。",
        )
    if buffer_hash != _build_editor_buffer_hash(current_content):
        raise ProjectDocumentMutationError(
            "write_grant_expired",
            "当前写回授权缓冲区已变化，请刷新当前文稿后再尝试写入。",
        )


def _build_editor_buffer_hash(content: str) -> str:
    hash_value = 0xCBF29CE484222325
    for character in content:
        hash_value ^= ord(character)
        hash_value = (hash_value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"fnv1a64:{hash_value:016x}"


def _validate_document_content(content: str, *, schema_id: str | None, path: str) -> None:
    if not path.endswith(".json"):
        return
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProjectDocumentMutationError(
            "invalid_json",
            f"目标 JSON 文稿不是合法 JSON：{exc.msg}",
        ) from exc
    if schema_id is None:
        return
    _validate_schema_bound_json(schema_id, parsed)


def _validate_schema_bound_json(schema_id: str, payload: object) -> None:
    try:
        validate_project_document_schema(schema_id, payload)
    except ProjectDocumentSchemaValidationError as exc:
        raise ProjectDocumentMutationError(
            "schema_validation_failed",
            str(exc),
        ) from exc
