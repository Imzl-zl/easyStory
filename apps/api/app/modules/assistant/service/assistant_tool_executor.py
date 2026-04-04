from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.service import ProjectDocumentCapabilityService
from app.shared.runtime.errors import ConfigurationError

from .assistant_tool_runtime_dto import (
    AssistantToolExecutionContext,
    AssistantToolResultEnvelope,
)


class ProjectReadDocumentsToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(min_length=1)
    cursors: list[str] = Field(default_factory=list)


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
    ) -> AssistantToolResultEnvelope:
        if context.execution_locus != "local_runtime":
            raise ConfigurationError(f"Unsupported execution_locus: {context.execution_locus}")
        if context.tool_name != "project.read_documents":
            raise ConfigurationError(f"Unsupported tool_name: {context.tool_name}")
        if context.project_id is None:
            raise ConfigurationError("project.read_documents requires project_id")
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
            content_items=_build_content_items(result.documents),
            resource_links=_build_resource_links(result.documents),
            error=None,
            audit=None,
        )


def _build_content_items(documents: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in documents:
        items.append(
            {
                "type": "text",
                "text": f"{item.path}\n\n{item.content}",
            }
        )
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
