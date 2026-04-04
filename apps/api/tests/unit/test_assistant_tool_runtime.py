import asyncio
import uuid

from app.modules.assistant.service import (
    AssistantToolDescriptorRegistry,
    AssistantToolExecutor,
    AssistantToolExposurePolicy,
)
from app.modules.assistant.service.assistant_tool_runtime_dto import (
    AssistantToolExecutionContext,
    AssistantToolExposureContext,
)
from app.modules.project.infrastructure import ProjectDocumentFileStore, ProjectDocumentIdentityStore
from app.modules.project.service import ProjectDocumentCapabilityService, ProjectService
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, ready_project_setting


def test_assistant_tool_descriptor_registry_exposes_project_read_documents_descriptor():
    registry = AssistantToolDescriptorRegistry()

    descriptor = registry.get_descriptor("project.read_documents")

    assert descriptor is not None
    assert descriptor.execution_locus == "local_runtime"
    assert descriptor.approval_mode == "none"
    assert descriptor.plane == "resource"
    assert descriptor.mutability == "read_only"
    assert descriptor.origin == "project_document"
    assert descriptor.trust_class == "local_first_party"


def test_assistant_tool_exposure_policy_only_exposes_project_tools_inside_project_scope():
    registry = AssistantToolDescriptorRegistry()
    policy = AssistantToolExposurePolicy(registry=registry)

    assert (
        policy.resolve_visible_tools(
            context=AssistantToolExposureContext(
                project_id=None,
                requested_write_scope="disabled",
            )
        )
        == []
    )
    assert [item.name for item in policy.resolve_visible_tools(
        context=AssistantToolExposureContext(
            project_id=uuid.uuid4(),
            requested_write_scope="disabled",
        )
    )] == [
        "project.read_documents"
    ]


def test_assistant_tool_executor_executes_project_read_documents(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n林渊")
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)

    result = asyncio.run(
        executor.execute(
            async_db(db),
            AssistantToolExecutionContext(
                owner_id=project.owner_id,
                project_id=project.id,
                arguments={"paths": ["设定/人物.md"]},
                tool_call_id="tool-call-1",
                tool_name="project.read_documents",
                execution_locus="local_runtime",
            ),
        )
    )

    assert result.tool_call_id == "tool-call-1"
    assert result.status == "completed"
    assert result.structured_output["documents"][0]["path"] == "设定/人物.md"
    assert result.resource_links[0]["document_ref"].startswith("project_file:")
    assert "林渊" in result.content_items[0]["text"]
