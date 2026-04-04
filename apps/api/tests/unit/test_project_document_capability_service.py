import asyncio

from app.modules.project.infrastructure import ProjectDocumentFileStore, ProjectDocumentIdentityStore
from app.modules.project.service import (
    ProjectDocumentEntryCreateDTO,
    ProjectDocumentCapabilityService,
    ProjectDocumentEntryRenameDTO,
    ProjectDocumentSaveDTO,
    ProjectService,
)
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_content, create_content_version, create_project, ready_project_setting


def test_project_document_capability_catalog_includes_canonical_and_file_entries(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    outline = create_content(
        db,
        project=project,
        content_type="outline",
        title="总大纲",
        chapter_number=None,
    )
    create_content_version(db, content=outline, content_text="这是正式大纲内容", version_number=1)
    db.commit()

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

    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))

    by_path = {item.path: item for item in catalog}
    assert by_path["大纲/总大纲.md"].document_ref == "canonical:outline"
    assert by_path["大纲/总大纲.md"].source == "outline"
    assert by_path["大纲/总大纲.md"].writable is False
    assert by_path["设定/人物.md"].source == "file"
    assert by_path["设定/人物.md"].writable is True
    assert by_path["设定/人物.md"].document_ref.startswith("project_file:")
    assert by_path["设定/人物.md"].resource_uri.startswith(f"project-document://{project.id}/")
    assert len({item.catalog_version for item in catalog}) == 1


def test_project_document_capability_read_documents_returns_content(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    file_store.save_project_document(project.id, "数据层/人物关系.json", '{\n  "relations": []\n}')
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )

    result = asyncio.run(
        capability_service.read_documents(
            async_db(db),
            project.id,
            paths=["数据层/人物关系.json", "设定/不存在.md"],
        )
    )

    assert result.documents[0].path == "数据层/人物关系.json"
    assert result.documents[0].schema_id == "project.character_relations"
    assert '"relations": []' in result.documents[0].content
    assert result.errors[0].path == "设定/不存在.md"
    assert result.errors[0].code == "document_not_found"


def test_project_document_capability_returns_error_for_missing_canonical_document(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )

    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    outline_entry = next(item for item in catalog if item.path == "大纲/总大纲.md")
    assert outline_entry.content_state == "placeholder"

    result = asyncio.run(
        capability_service.read_documents(
            async_db(db),
            project.id,
            paths=["大纲/总大纲.md"],
        )
    )

    assert result.documents == []
    assert result.errors[0].path == "大纲/总大纲.md"
    assert result.errors[0].code == "document_not_readable"


def test_project_document_capability_read_documents_truncates_with_stable_cursor(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    long_text = "A" * 4500 + "B" * 200
    file_store.save_project_document(project.id, "附录/长文稿.md", long_text)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )

    first_page = asyncio.run(
        capability_service.read_documents(
            async_db(db),
            project.id,
            paths=["附录/长文稿.md"],
        )
    )
    first_item = first_page.documents[0]
    assert first_item.truncated is True
    assert first_item.next_cursor == "offset:4000"
    assert len(first_item.content) == 4000

    second_page = asyncio.run(
        capability_service.read_documents(
            async_db(db),
            project.id,
            paths=["附录/长文稿.md"],
            cursors=["offset:4000"],
        )
    )
    second_item = second_page.documents[0]
    assert second_item.truncated is False
    assert second_item.next_cursor is None
    assert second_item.content == long_text[4000:]


def test_project_document_capability_keeps_file_document_ref_stable_after_rename(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    file_store.save_project_document(project.id, "附录/旧灵感.md", "旧内容")

    before = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    before_ref = next(item.document_ref for item in before if item.path == "附录/旧灵感.md")

    asyncio.run(
        project_service.rename_project_document_entry(
            async_db(db),
            project.id,
            ProjectDocumentEntryRenameDTO(
                path="附录/旧灵感.md",
                next_path="附录/新灵感.md",
            ),
        )
    )

    after = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    after_entry = next(item for item in after if item.path == "附录/新灵感.md")
    assert after_entry.document_ref == before_ref


def test_project_document_capability_keeps_nested_file_document_ref_stable_after_folder_rename(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    asyncio.run(
        project_service.create_project_document_entry(
            async_db(db),
            project.id,
            ProjectDocumentEntryCreateDTO(kind="folder", path="附录/旧目录"),
        )
    )
    asyncio.run(
        project_service.save_project_document(
            async_db(db),
            project.id,
            "附录/旧目录/灵感.md",
            ProjectDocumentSaveDTO(content="旧内容"),
        )
    )

    before = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    before_ref = next(item.document_ref for item in before if item.path == "附录/旧目录/灵感.md")

    asyncio.run(
        project_service.rename_project_document_entry(
            async_db(db),
            project.id,
            ProjectDocumentEntryRenameDTO(
                path="附录/旧目录",
                next_path="附录/新目录",
            ),
        )
    )

    after = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    after_entry = next(item for item in after if item.path == "附录/新目录/灵感.md")
    assert after_entry.document_ref == before_ref
