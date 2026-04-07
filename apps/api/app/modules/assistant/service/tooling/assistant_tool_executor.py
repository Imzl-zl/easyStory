from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.service import ProjectDocumentCapabilityService
from app.modules.project.service.dto import ProjectDocumentSource
from app.modules.project.service.project_document_capability_dto import ProjectDocumentContentState
from app.modules.project.service.project_document_buffer_state_support import (
    extract_trusted_project_document_buffer_snapshot,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .assistant_tool_runtime_dto import (
    AssistantToolExecutionContext,
    AssistantToolLifecycleRecorder,
    AssistantToolLifecycleUpdate,
    AssistantToolResultEnvelope,
)

PROJECT_SEARCH_DOCUMENTS_DEFAULT_LIMIT = 8
PROJECT_SEARCH_DOCUMENTS_MAX_LIMIT = 20


def _normalize_optional_search_argument(value: object, *, field_name: str) -> object:
    if value is None or not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} 不能为空")
    return normalized


def _normalize_required_search_tokens(value: object, *, field_name: str) -> object:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return value
    normalized_items: list[object] = []
    for item in value:
        if not isinstance(item, str):
            normalized_items.append(item)
            continue
        normalized = item.strip()
        if not normalized:
            raise ValueError(f"{field_name} 不能包含空白项")
        normalized_items.append(normalized)
    return normalized_items


class ProjectListDocumentsToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectReadDocumentsToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(min_length=1)
    cursors: list[str] = Field(default_factory=list)

    @field_validator("paths", "cursors", mode="before")
    @classmethod
    def validate_string_lists(cls, value: object, info) -> object:
        return _normalize_required_search_tokens(value, field_name=info.field_name)

    @model_validator(mode="after")
    def validate_cursor_alignment(self) -> "ProjectReadDocumentsToolArgs":
        if self.cursors and len(self.cursors) != len(self.paths):
            raise ValueError("cursors must align with paths")
        return self


class ProjectSearchDocumentsToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, min_length=1)
    path_prefix: str | None = Field(default=None, min_length=1)
    sources: list[ProjectDocumentSource] = Field(default_factory=list)
    schema_ids: list[str] = Field(default_factory=list)
    content_states: list[ProjectDocumentContentState] = Field(default_factory=list)
    writable: bool | None = None
    limit: int = Field(
        default=PROJECT_SEARCH_DOCUMENTS_DEFAULT_LIMIT,
        ge=1,
        le=PROJECT_SEARCH_DOCUMENTS_MAX_LIMIT,
    )

    @field_validator("query", "path_prefix", mode="before")
    @classmethod
    def validate_search_text(cls, value: object, info) -> object:
        return _normalize_optional_search_argument(value, field_name=info.field_name)

    @field_validator("schema_ids", mode="before")
    @classmethod
    def validate_schema_ids(cls, value: object) -> object:
        return _normalize_required_search_tokens(value, field_name="schema_ids")

    @model_validator(mode="after")
    def validate_search_constraints(self) -> "ProjectSearchDocumentsToolArgs":
        if any(
            (
                self.query,
                self.path_prefix,
                self.sources,
                self.schema_ids,
                self.content_states,
                self.writable is not None,
            )
        ):
            return self
        raise ValueError("project.search_documents requires at least one query or filter")


class ProjectWriteDocumentToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    content: str
    base_version: str = Field(min_length=1)


class AssistantToolTerminalRunError(BusinessRuleError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AssistantToolExecutor:
    def __init__(
        self,
        *,
        project_document_capability_service: ProjectDocumentCapabilityService,
    ) -> None:
        self.project_document_capability_service = project_document_capability_service

    async def execute(
        self,
        db: AsyncSession,
        context: AssistantToolExecutionContext,
        *,
        on_lifecycle_update: AssistantToolLifecycleRecorder | None = None,
    ) -> AssistantToolResultEnvelope:
        if context.execution_locus != "local_runtime":
            raise ConfigurationError(f"Unsupported execution_locus: {context.execution_locus}")
        if context.project_id is None:
            raise ConfigurationError(f"{context.tool_name} requires project_id")
        if context.tool_name == "project.list_documents":
            return await self._execute_list_documents(db, context)
        if context.tool_name == "project.read_documents":
            return await self._execute_read_documents(db, context)
        if context.tool_name == "project.search_documents":
            return await self._execute_search_documents(db, context)
        if context.tool_name == "project.write_document":
            return await self._execute_write_document(
                db,
                context,
                on_lifecycle_update=on_lifecycle_update,
            )
        raise ConfigurationError(f"Unsupported tool_name: {context.tool_name}")

    async def _execute_list_documents(
        self,
        db: AsyncSession,
        context: AssistantToolExecutionContext,
    ) -> AssistantToolResultEnvelope:
        ProjectListDocumentsToolArgs.model_validate(context.arguments)
        catalog = await self.project_document_capability_service.list_document_catalog(
            db,
            context.project_id,
            owner_id=context.owner_id,
        )
        if not catalog:
            raise ConfigurationError("Project document catalog must not be empty")
        return AssistantToolResultEnvelope(
            tool_call_id=context.tool_call_id,
            status="completed",
            structured_output={
                "documents": [item.model_dump(mode="json") for item in catalog],
                "catalog_version": catalog[0].catalog_version,
            },
            content_items=_build_catalog_content_items(catalog),
            resource_links=_build_resource_links(catalog),
            error=None,
            audit=None,
        )

    async def _execute_read_documents(
        self,
        db: AsyncSession,
        context: AssistantToolExecutionContext,
    ) -> AssistantToolResultEnvelope:
        arguments = ProjectReadDocumentsToolArgs.model_validate(context.arguments)
        result = await self.project_document_capability_service.read_documents(
            db,
            context.project_id,
            paths=arguments.paths,
            cursors=arguments.cursors,
            owner_id=context.owner_id,
        )
        return AssistantToolResultEnvelope(
            tool_call_id=context.tool_call_id,
            status="completed",
            structured_output=result.model_dump(mode="json"),
            content_items=_build_read_content_items(result),
            resource_links=_build_resource_links(result.documents),
            error=None,
            audit=None,
        )

    async def _execute_search_documents(
        self,
        db: AsyncSession,
        context: AssistantToolExecutionContext,
    ) -> AssistantToolResultEnvelope:
        arguments = ProjectSearchDocumentsToolArgs.model_validate(context.arguments)
        result = await self.project_document_capability_service.search_documents(
            db,
            context.project_id,
            query=arguments.query,
            path_prefix=arguments.path_prefix,
            sources=arguments.sources,
            schema_ids=arguments.schema_ids,
            content_states=arguments.content_states,
            writable=arguments.writable,
            limit=arguments.limit,
            owner_id=context.owner_id,
        )
        return AssistantToolResultEnvelope(
            tool_call_id=context.tool_call_id,
            status="completed",
            structured_output=result.model_dump(mode="json"),
            content_items=_build_search_content_items(result),
            resource_links=_build_search_resource_links(result.documents),
            error=None,
            audit=None,
        )

    async def _execute_write_document(
        self,
        db: AsyncSession,
        context: AssistantToolExecutionContext,
        *,
        on_lifecycle_update: AssistantToolLifecycleRecorder | None = None,
    ) -> AssistantToolResultEnvelope:
        arguments = ProjectWriteDocumentToolArgs.model_validate(context.arguments)
        _validate_write_execution_context(context)
        prepared_write = await self.project_document_capability_service.prepare_write_document(
            db,
            context.project_id,
            path=arguments.path,
            content=arguments.content,
            base_version=arguments.base_version,
            owner_id=context.owner_id,
            expected_document_ref=context.active_document_ref,
            expected_binding_version=context.active_binding_version,
            active_buffer_state=context.active_buffer_state,
            allowed_target_document_refs=context.allowed_target_document_refs,
            require_trusted_buffer_state=True,
            run_audit_id=context.run_audit_id,
        )
        if on_lifecycle_update is not None:
            on_lifecycle_update(
                AssistantToolLifecycleUpdate(
                    status="writing",
                    target_document_refs=(prepared_write.resolved_document.document_ref,),
                )
            )
        result = await self.project_document_capability_service.commit_prepared_write_document(
            db,
            prepared_write,
        )
        return AssistantToolResultEnvelope(
            tool_call_id=context.tool_call_id,
            status="completed",
            structured_output=result.model_dump(mode="json"),
            content_items=[
                {
                    "type": "text",
                    "text": _build_write_result_text(result),
                },
            ],
            resource_links=[
                {
                    "path": result.path,
                    "document_ref": result.document_ref,
                    "resource_uri": result.resource_uri,
                }
            ],
            error=None,
            audit={"run_audit_id": result.run_audit_id},
        )


def _build_catalog_content_items(documents: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in documents:
        text_lines = [
            item.path,
            f"document_ref={item.document_ref}",
            f"source={item.source}",
            f"document_kind={item.document_kind}",
            f"version={item.version}",
            f"content_state={item.content_state}",
            f"writable={str(item.writable).lower()}",
        ]
        if item.schema_id is not None:
            text_lines.append(f"schema_id={item.schema_id}")
        items.append(
            {
                "type": "text",
                "text": "\n".join(text_lines),
            }
        )
    return items


def _build_read_content_items(result: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in result.documents:
        text_lines = [
            item.path,
            f"document_ref={item.document_ref}",
            f"version={item.version}",
            f"truncated={str(item.truncated).lower()}",
        ]
        if item.next_cursor is not None:
            text_lines.append(f"next_cursor={item.next_cursor}")
        if item.schema_id is not None:
            text_lines.append(f"schema_id={item.schema_id}")
        text_lines.extend(("", item.content))
        items.append(
            {
                "type": "text",
                "text": "\n".join(text_lines),
            }
        )
    for error in result.errors:
        items.append(
            {
                "type": "text",
                "text": "\n".join(
                    [
                        f"path={error.path}",
                        f"code={error.code}",
                        error.message,
                    ]
                ),
            }
        )
    return items


def _build_search_content_items(result: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in result.documents:
        text_lines = [
            item.path,
            f"document_ref={item.document_ref}",
            f"title={item.title}",
            f"source={item.source}",
            f"document_kind={item.document_kind}",
            f"content_state={item.content_state}",
            f"writable={str(item.writable).lower()}",
            f"match_score={item.match_score}",
        ]
        if item.schema_id is not None:
            text_lines.append(f"schema_id={item.schema_id}")
        if item.matched_fields:
            text_lines.append(f"matched_fields={','.join(item.matched_fields)}")
        items.append({"type": "text", "text": "\n".join(text_lines)})
    return items


def _build_resource_links(documents: list[Any]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for item in documents:
        links.append(
            {
                "path": item.path,
                "document_ref": item.document_ref,
                "resource_uri": item.resource_uri,
            }
        )
    return links


def _build_search_resource_links(documents: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "path": item.path,
            "document_ref": item.document_ref,
            "resource_uri": item.resource_uri,
        }
        for item in documents
    ]


def _validate_write_execution_context(context: AssistantToolExecutionContext) -> None:
    if context.requested_write_scope != "turn":
        raise AssistantToolTerminalRunError(
            "write_not_authorized",
            "当前 turn 没有启用文稿写回能力。",
        )
    if len(context.allowed_target_document_refs) != 1:
        raise AssistantToolTerminalRunError(
            "write_target_not_allowed",
            "当前 turn 没有可写的目标文稿。",
        )
    approval_grant = context.approval_grant
    if approval_grant is None:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权已失效，请重新发起本轮请求。",
        )
    if context.tool_name not in approval_grant.allowed_tool_names:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权不允许执行这个工具。",
        )
    active_document_ref = context.active_document_ref
    if active_document_ref is None:
        raise AssistantToolTerminalRunError(
            "write_target_not_allowed",
            "当前 turn 没有绑定可写的活动文稿。",
        )
    if context.allowed_target_document_refs[0] != active_document_ref:
        raise AssistantToolTerminalRunError(
            "write_target_not_allowed",
            "当前 turn 的写入授权与活动文稿不一致。",
        )
    if tuple(approval_grant.target_document_refs) != context.allowed_target_document_refs:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权与目标文稿约束不一致。",
        )
    if context.active_binding_version is None:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权已失效，请重新发起本轮请求。",
        )
    grant_binding_version = approval_grant.binding_version_constraints.get(active_document_ref)
    if grant_binding_version != context.active_binding_version:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权的 binding_version 已失效，请重新发起本轮请求。",
        )
    trusted_snapshot = extract_trusted_project_document_buffer_snapshot(
        context.active_buffer_state
    )
    if trusted_snapshot is None:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权的缓冲区快照已失效，请重新发起本轮请求。",
        )
    grant_base_version = approval_grant.base_version_constraints.get(active_document_ref)
    if grant_base_version != trusted_snapshot.base_version:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权的 base_version 已失效，请重新发起本轮请求。",
        )
    grant_buffer_hash = approval_grant.buffer_hash_constraints.get(active_document_ref)
    if grant_buffer_hash != trusted_snapshot.buffer_hash:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权的缓冲区哈希已失效，请重新发起本轮请求。",
        )
    grant_buffer_source = approval_grant.buffer_source_constraints.get(active_document_ref)
    if grant_buffer_source != trusted_snapshot.source:
        raise AssistantToolTerminalRunError(
            "write_grant_expired",
            "当前写回授权的缓冲区来源已失效，请重新发起本轮请求。",
        )


def _build_write_result_text(result: Any) -> str:
    return (
        f"{result.path} 已写回完成。\n"
        f"version={result.version}\n"
        f"document_revision_id={result.document_revision_id}"
    )
