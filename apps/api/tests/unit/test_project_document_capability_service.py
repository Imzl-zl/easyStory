import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import threading
from types import SimpleNamespace
import uuid

import pytest

from app.modules.content.service import CanonicalProjectDocumentDTO
from app.modules.project.infrastructure import (
    ProjectDocumentFileStore,
    ProjectDocumentIdentityStore,
    ProjectDocumentRevisionStore,
)
from app.modules.project.service import (
    ProjectDocumentEntryCreateDTO,
    ProjectDocumentCapabilityService,
    ProjectDocumentEntryRenameDTO,
    ProjectDocumentSaveDTO,
    ProjectService,
)
from app.modules.project.service.project_document_buffer_state_support import (
    TRUSTED_ACTIVE_BUFFER_SOURCE,
    build_project_document_buffer_hash,
)
from app.modules.project.service.project_document_capability_service import (
    ProjectDocumentMutationError,
    _build_catalog_version,
)
from app.modules.project.service.project_document_version_support import (
    build_project_file_document_version,
)
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_content, create_content_version, create_project, ready_project_setting


def _build_trusted_active_buffer_state(
    *,
    base_version: str,
    content: str,
    dirty: bool = False,
) -> dict[str, object]:
    return {
        "dirty": dirty,
        "base_version": base_version,
        "buffer_hash": build_project_document_buffer_hash(content),
        "source": TRUSTED_ACTIVE_BUFFER_SOURCE,
    }


class _FailOnAppendRevisionStore(ProjectDocumentRevisionStore):
    def append_revision(self, *args, **kwargs):
        raise RuntimeError("append revision failed")

    def append_revision_unlocked(self, *args, **kwargs):
        raise RuntimeError("append revision failed")


class _MetadataOnlyCatalogFileStore(ProjectDocumentFileStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata_reads = 0

    def find_project_document(self, *args, **kwargs):
        raise AssertionError("catalog path should not read full document content")

    def find_project_document_metadata(self, *args, **kwargs):
        self.metadata_reads += 1
        return super().find_project_document_metadata(*args, **kwargs)


class _TrackingRevisionStore(ProjectDocumentRevisionStore):
    def __init__(self, root):
        super().__init__(root)
        self.lock_depth = 0

    @contextmanager
    def revision_lock(self, project_id):
        self.lock_depth += 1
        try:
            with super().revision_lock(project_id):
                yield
        finally:
            self.lock_depth -= 1


class _LockAwareFileStore(ProjectDocumentFileStore):
    def __init__(self, root, *, revision_store: _TrackingRevisionStore):
        super().__init__(root)
        self.revision_store = revision_store
        self.require_lock_for_save = False

    def save_project_document(self, *args, **kwargs):
        if self.require_lock_for_save:
            assert self.revision_store.lock_depth > 0
        return super().save_project_document(*args, **kwargs)


class _TrackingDocumentReadFileStore(ProjectDocumentFileStore):
    def __init__(self, root):
        super().__init__(root)
        self.document_reads: list[str] = []

    def find_project_document(self, project_id, document_path):
        self.document_reads.append(document_path)
        return super().find_project_document(project_id, document_path)


class _SelectiveCanonicalDocumentQueryService:
    def __init__(
        self,
        *,
        full_documents: list[CanonicalProjectDocumentDTO] | None = None,
        selected_documents: list[CanonicalProjectDocumentDTO] | None = None,
    ) -> None:
        self.full_include_content_calls: list[bool] = []
        self.selected_calls: list[dict[str, object]] = []
        self.full_documents = list(full_documents or [])
        self.selected_documents = list(selected_documents or [])

    async def list_canonical_documents(self, db, project_id, *, include_content=False):
        del db, project_id
        self.full_include_content_calls.append(include_content)
        if include_content:
            raise AssertionError("full canonical content load should not be used here")
        return list(self.full_documents)

    async def list_selected_canonical_documents(
        self,
        db,
        project_id,
        *,
        include_content=False,
        include_outline=False,
        include_opening_plan=False,
        chapter_numbers=(),
    ):
        del db, project_id
        normalized_chapter_numbers = tuple(sorted(set(chapter_numbers)))
        self.selected_calls.append(
            {
                "include_content": include_content,
                "include_outline": include_outline,
                "include_opening_plan": include_opening_plan,
                "chapter_numbers": normalized_chapter_numbers,
            }
        )
        return [
            item
            for item in self.selected_documents
            if (
                (include_outline and item.content_type == "outline")
                or (include_opening_plan and item.content_type == "opening_plan")
                or (
                    item.content_type == "chapter"
                    and item.chapter_number in normalized_chapter_numbers
                )
            )
        ]


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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
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


def test_project_document_capability_catalog_uses_metadata_only_file_resolution(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = _MetadataOnlyCatalogFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )

    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    assert target.document_ref.startswith("project_file:")
    assert file_store.metadata_reads >= 1


def test_project_document_capability_catalog_requires_identity_store_for_file_documents(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(document_file_store=file_store),
        document_file_store=file_store,
    )

    with pytest.raises(RuntimeError, match="identity store"):
        asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))


def test_project_document_catalog_version_includes_entry_metadata() -> None:
    base = _build_catalog_record()

    title_changed = _build_catalog_record(title="人物设定")
    schema_changed = _build_catalog_record(schema_id="project.factions")
    content_state_changed = _build_catalog_record(content_state="placeholder")

    assert _build_catalog_version([base]) != _build_catalog_version([title_changed])
    assert _build_catalog_version([base]) != _build_catalog_version([schema_changed])
    assert _build_catalog_version([base]) != _build_catalog_version([content_state_changed])


def test_project_document_capability_search_documents_matches_query_and_filters(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    file_store.save_project_document(
        project.id,
        "数据层/人物关系.json",
        '{\n  "character_relations": []\n}',
    )
    file_store.save_project_document(project.id, "时间轴/章节索引.md", "# 章节索引\n\n第一卷")
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )

    result = asyncio.run(
        capability_service.search_documents(
            async_db(db),
            project.id,
            query="人物关系",
            sources=["file"],
            schema_ids=["project.character_relations"],
            writable=True,
            limit=5,
        )
    )

    assert result.catalog_version.startswith("catalog:")
    assert [item.path for item in result.documents] == ["数据层/人物关系.json"]
    hit = result.documents[0]
    assert set(hit.matched_fields) >= {"path", "title"}
    assert hit.match_score > 0
    assert hit.schema_id == "project.character_relations"


def test_project_document_capability_search_documents_uses_metadata_only_file_resolution(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = _MetadataOnlyCatalogFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
    )

    result = asyncio.run(
        capability_service.search_documents(
            async_db(db),
            project.id,
            query="人物",
        )
    )

    assert result.documents[0].path == "设定/人物.md"
    assert file_store.metadata_reads >= 1


def test_project_document_capability_search_documents_rejects_blank_query(db, tmp_path):
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

    with pytest.raises(ValueError, match="query"):
        asyncio.run(
            capability_service.search_documents(
                async_db(db),
                project.id,
                query="   ",
            )
        )


def test_project_document_capability_search_documents_matches_placeholder_content_state(db, tmp_path):
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

    result = asyncio.run(
        capability_service.search_documents(
            async_db(db),
            project.id,
            path_prefix="大纲/总",
            content_states=["placeholder"],
        )
    )

    assert [item.path for item in result.documents] == ["大纲/总大纲.md"]
    assert result.documents[0].content_state == "placeholder"


def test_project_document_capability_search_documents_prioritizes_continuity_documents(db, tmp_path):
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
    file_store.save_project_document(project.id, "数据层/人物关系.json", '{"relations":[]}')
    file_store.save_project_document(project.id, "数据层/势力关系.json", '{"relations":[]}')
    file_store.save_project_document(project.id, "时间轴/章节索引.md", "# 章节索引")
    file_store.save_project_document(project.id, "校验/伏笔回收清单.md", "# 伏笔回收")
    file_store.save_project_document(project.id, "附录/灵感碎片.md", "# 灵感碎片")

    result = asyncio.run(
        capability_service.search_documents(
            async_db(db),
            project.id,
            query="连续性",
            limit=4,
        )
    )

    returned_paths = [item.path for item in result.documents]

    assert len(returned_paths) == 4
    assert "附录/灵感碎片.md" not in returned_paths
    assert set(returned_paths) == {
        "数据层/人物关系.json",
        "数据层/势力关系.json",
        "时间轴/章节索引.md",
        "校验/伏笔回收清单.md",
    }


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


def test_project_document_capability_read_documents_uses_targeted_file_resolution(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = _TrackingDocumentReadFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    file_store.save_project_document(project.id, "附录/灵感.md", "# 灵感\n\n不要被读到")
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
            paths=["设定/人物.md"],
        )
    )

    assert [item.path for item in result.documents] == ["设定/人物.md"]
    assert file_store.document_reads == ["设定/人物.md"]


def test_project_document_capability_read_documents_uses_targeted_canonical_resolution(db, tmp_path):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    outline = CanonicalProjectDocumentDTO(
        project_id=project.id,
        content_id=uuid.uuid4(),
        content_type="outline",
        title="总大纲",
        content_text="这是正式大纲内容",
        version_number=1,
        word_count=8,
    )
    canonical_query_service = _SelectiveCanonicalDocumentQueryService(
        full_documents=[outline.model_copy(update={"content_text": ""})],
        selected_documents=[outline],
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
        canonical_document_query_service=canonical_query_service,
    )

    result = asyncio.run(
        capability_service.read_documents(
            async_db(db),
            project.id,
            paths=["大纲/总大纲.md"],
        )
    )

    assert result.documents[0].content == "这是正式大纲内容"
    assert canonical_query_service.full_include_content_calls == [False]
    assert canonical_query_service.selected_calls == [
        {
            "include_content": True,
            "include_outline": True,
            "include_opening_plan": False,
            "chapter_numbers": (),
        }
    ]


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


def test_project_document_capability_read_documents_aligns_duplicate_paths_with_distinct_cursors(
    db,
    tmp_path,
):
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

    result = asyncio.run(
        capability_service.read_documents(
            async_db(db),
            project.id,
            paths=["附录/长文稿.md", "附录/长文稿.md"],
            cursors=["offset:0", "offset:4000"],
        )
    )

    assert [item.path for item in result.documents] == ["附录/长文稿.md", "附录/长文稿.md"]
    assert result.documents[0].content == long_text[:4000]
    assert result.documents[0].next_cursor == "offset:4000"
    assert result.documents[1].content == long_text[4000:]
    assert result.documents[1].next_cursor is None


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
            ProjectDocumentSaveDTO(
                base_version=build_project_file_document_version(""),
                content="旧内容",
            ),
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


def test_project_document_capability_write_document_returns_version_revision_and_audit(db, tmp_path):
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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    result = asyncio.run(
        capability_service.write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            base_version=target.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
            allowed_target_document_refs=(target.document_ref,),
            require_trusted_buffer_state=True,
            run_audit_id="run-audit-1",
        )
    )

    assert result.path == "设定/人物.md"
    assert result.document_ref == target.document_ref
    assert result.version.startswith("sha256:")
    assert result.document_revision_id
    assert result.diff_summary.changed is True
    assert result.run_audit_id == "run-audit-1"

    repeated = asyncio.run(
        capability_service.write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            base_version=result.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=result.version,
                content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            ),
            allowed_target_document_refs=(target.document_ref,),
            require_trusted_buffer_state=True,
            run_audit_id="run-audit-1-repeat",
        )
    )

    assert repeated.document_revision_id != result.document_revision_id
    assert repeated.diff_summary.changed is False


def test_project_document_capability_prepare_write_document_uses_targeted_file_resolution(
    db,
    tmp_path,
):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = _TrackingDocumentReadFileStore(tmp_path)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    canonical_query_service = _SelectiveCanonicalDocumentQueryService()
    capability_service = ProjectDocumentCapabilityService(
        project_service=ProjectService(
            document_file_store=file_store,
            document_identity_store=identity_store,
        ),
        document_file_store=file_store,
        document_identity_store=identity_store,
        canonical_document_query_service=canonical_query_service,
    )
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    file_store.save_project_document(project.id, "附录/灵感.md", "# 灵感\n\n不要被读到")

    prepared = asyncio.run(
        capability_service.prepare_write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            base_version=build_project_file_document_version(current_content),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=build_project_file_document_version(current_content),
                content=current_content,
            ),
            run_audit_id="run-audit-targeted-prepare",
        )
    )

    assert prepared.path == "设定/人物.md"
    assert file_store.document_reads == ["设定/人物.md"]
    assert canonical_query_service.full_include_content_calls == []
    assert canonical_query_service.selected_calls == []


def test_project_document_capability_write_document_reuses_revision_for_same_run_audit_id(db, tmp_path):
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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    first = asyncio.run(
        capability_service.write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            base_version=target.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
            allowed_target_document_refs=(target.document_ref,),
            require_trusted_buffer_state=True,
            run_audit_id="run-audit-idempotent",
        )
    )
    repeated = asyncio.run(
        capability_service.write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            base_version=first.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=first.version,
                content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            ),
            allowed_target_document_refs=(target.document_ref,),
            require_trusted_buffer_state=True,
            run_audit_id="run-audit-idempotent",
        )
    )

    assert repeated.document_revision_id == first.document_revision_id
    assert repeated.run_audit_id == first.run_audit_id
    assert repeated.diff_summary.changed is False


def test_project_document_capability_commit_prepared_write_document_surfaces_effective_write_on_revision_failure(
    db,
    tmp_path,
):
    project = create_project(db, project_setting=ready_project_setting())
    file_store = ProjectDocumentFileStore(tmp_path / "documents")
    identity_store = ProjectDocumentIdentityStore(tmp_path / "documents")
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
        document_revision_store=_FailOnAppendRevisionStore(tmp_path / "revisions"),
    )
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    prepared = asyncio.run(
        capability_service.prepare_write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            base_version=target.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
            allowed_target_document_refs=(target.document_ref,),
            require_trusted_buffer_state=True,
            run_audit_id="run-audit-failing-revision",
        )
    )

    try:
        asyncio.run(
            capability_service.commit_prepared_write_document(
                async_db(db),
                prepared,
            )
        )
    except ProjectDocumentMutationError as exc:
        assert exc.code == "document_revision_persist_failed"
        assert getattr(exc, "write_effective", False) is True
    else:
        raise AssertionError("expected document_revision_persist_failed")

    saved = file_store.find_project_document(project.id, "设定/人物.md")
    assert saved is not None
    assert "新增：夜雨观察力极强。" in saved.content


def test_project_document_capability_write_document_recovers_missing_revision_for_same_run_audit_id(
    db,
    tmp_path,
):
    project = create_project(db, project_setting=ready_project_setting())
    document_root = tmp_path / "documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    failing_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
        document_revision_store=_FailOnAppendRevisionStore(tmp_path / "revisions"),
    )
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(failing_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")
    content = "# 人物\n\n林渊\n\n新增：夜雨观察力极强。"

    with pytest.raises(ProjectDocumentMutationError) as exc_info:
        asyncio.run(
            failing_service.write_document(
                async_db(db),
                project.id,
                path="设定/人物.md",
                content=content,
                base_version=target.version,
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                active_buffer_state=_build_trusted_active_buffer_state(
                    base_version=target.version,
                    content=current_content,
                ),
                allowed_target_document_refs=(target.document_ref,),
                require_trusted_buffer_state=True,
                run_audit_id="run-audit-recovery",
            )
        )
    assert exc_info.value.code == "document_revision_persist_failed"

    recovery_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    recovered = asyncio.run(
        recovery_service.write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content=content,
            base_version=target.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=target.version,
                content=content,
            ),
            allowed_target_document_refs=(target.document_ref,),
            require_trusted_buffer_state=True,
            run_audit_id="run-audit-recovery",
        )
    )

    assert recovered.diff_summary.changed is False
    assert recovered.document_revision_id
    assert recovered.run_audit_id == "run-audit-recovery"


def test_project_document_revision_store_serializes_duplicate_run_audit_id_under_concurrency(
    tmp_path,
):
    store = ProjectDocumentRevisionStore(tmp_path)
    project_id = uuid.uuid4()
    worker_count = 8
    barrier = threading.Barrier(worker_count)

    def append_once(_: int):
        barrier.wait()
        return store.append_revision(
            project_id,
            document_ref="project_file:test",
            content_hash="hash-1",
            version="sha256:version-1",
            run_audit_id="run-audit-concurrent",
        )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(append_once, range(worker_count)))

    assert len({item.document_revision_id for item in results}) == 1
    revisions = store.list_revisions(project_id, document_ref="project_file:test")
    assert len(revisions) == 1
    assert revisions[0].run_audit_id == "run-audit-concurrent"


def test_project_document_capability_commit_holds_revision_lock_during_file_save(db, tmp_path):
    revision_store = _TrackingRevisionStore(tmp_path)
    file_store = _LockAwareFileStore(tmp_path, revision_store=revision_store)
    identity_store = ProjectDocumentIdentityStore(tmp_path)
    project = create_project(db, project_setting=ready_project_setting())
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    file_store.require_lock_for_save = True
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
        document_revision_store=revision_store,
    )
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    result = asyncio.run(
        capability_service.write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增观察力设定。",
            base_version=target.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            run_audit_id="run-audit-lock-order",
        )
    )

    assert result.run_audit_id == "run-audit-lock-order"


def test_project_document_capability_write_document_rejects_version_conflict(db, tmp_path):
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
    file_store.save_project_document(project.id, "数据层/人物关系.json", '{\n  "character_relations": []\n}')
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "数据层/人物关系.json")

    try:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="数据层/人物关系.json",
                content='{"character_relations":[]}',
                base_version="sha256:stale",
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                run_audit_id="run-audit-2",
            )
        )
    except ProjectDocumentMutationError as exc:
        assert exc.code == "version_conflict"
    else:
        raise AssertionError("expected version_conflict")


def test_project_document_capability_write_document_rejects_invalid_schema_bound_json(db, tmp_path):
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
    file_store.save_project_document(project.id, "数据层/人物关系.json", '{\n  "character_relations": []\n}')
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "数据层/人物关系.json")

    try:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="数据层/人物关系.json",
                content='{"relations":[]}',
                base_version=target.version,
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                run_audit_id="run-audit-3",
            )
        )
    except ProjectDocumentMutationError as exc:
        assert exc.code == "schema_validation_failed"
    else:
        raise AssertionError("expected schema_validation_failed")


def test_project_document_capability_write_document_rejects_incomplete_schema_bound_items(
    db,
    tmp_path,
):
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
    file_store.save_project_document(project.id, "数据层/人物.json", '{\n  "characters": []\n}')
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "数据层/人物.json")

    try:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="数据层/人物.json",
                content='{"characters":[{}]}',
                base_version=target.version,
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                run_audit_id="run-audit-3b",
            )
        )
    except ProjectDocumentMutationError as exc:
        assert exc.code == "schema_validation_failed"
        assert str(exc) == "目标数据文稿 characters[0].id 必须是非空字符串。"
    else:
        raise AssertionError("expected schema_validation_failed")


def test_project_document_capability_write_document_requires_trusted_buffer_state(db, tmp_path):
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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    try:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="设定/人物.md",
                content="# 人物\n\n林渊\n\n新增：谨慎。",
                base_version=target.version,
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                allowed_target_document_refs=(target.document_ref,),
                require_trusted_buffer_state=True,
                run_audit_id="run-audit-4",
            )
        )
    except ProjectDocumentMutationError as exc:
        assert exc.code == "active_buffer_state_required"
    else:
        raise AssertionError("expected active_buffer_state_required")


def test_project_document_capability_write_document_rejects_dirty_active_buffer(db, tmp_path):
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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    try:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="设定/人物.md",
                content="# 人物\n\n林渊\n\n新增：谨慎。",
                base_version=target.version,
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                active_buffer_state=_build_trusted_active_buffer_state(
                    base_version=target.version,
                    content=current_content,
                    dirty=True,
                ),
                allowed_target_document_refs=(target.document_ref,),
                require_trusted_buffer_state=True,
                run_audit_id="run-audit-5",
            )
        )
    except ProjectDocumentMutationError as exc:
        assert exc.code == "dirty_buffer_conflict"
    else:
        raise AssertionError("expected dirty_buffer_conflict")


def test_project_document_capability_write_document_rejects_stale_buffer_hash(db, tmp_path):
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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    with pytest.raises(ProjectDocumentMutationError) as exc_info:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="设定/人物.md",
                content="# 人物\n\n林渊\n\n新增：谨慎。",
                base_version=target.version,
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                active_buffer_state={
                    "dirty": False,
                    "base_version": target.version,
                    "buffer_hash": "fnv1a64:0000000000000000",
                    "source": TRUSTED_ACTIVE_BUFFER_SOURCE,
                },
                allowed_target_document_refs=(target.document_ref,),
                require_trusted_buffer_state=True,
                run_audit_id="run-audit-stale-buffer",
            )
        )

    assert exc_info.value.code == "write_grant_expired"


def test_project_document_capability_write_document_requires_trusted_buffer_source(db, tmp_path):
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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")

    with pytest.raises(ProjectDocumentMutationError) as exc_info:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="设定/人物.md",
                content="# 人物\n\n林渊\n\n新增：谨慎。",
                base_version=target.version,
                expected_document_ref=target.document_ref,
                expected_binding_version=_build_entry_binding_version(target),
                active_buffer_state={
                    "dirty": False,
                    "base_version": target.version,
                    "buffer_hash": build_project_document_buffer_hash(current_content),
                    "source": "external_editor",
                },
                allowed_target_document_refs=(target.document_ref,),
                require_trusted_buffer_state=True,
                run_audit_id="run-audit-untrusted-source",
            )
        )

    assert exc_info.value.code == "active_buffer_state_invalid"


def test_project_document_capability_write_document_rejects_revision_state_mismatch(db, tmp_path):
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
    current_content = "# 人物\n\n林渊"
    file_store.save_project_document(project.id, "设定/人物.md", current_content)
    catalog = asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
    target = next(item for item in catalog if item.path == "设定/人物.md")
    asyncio.run(
        capability_service.write_document(
            async_db(db),
            project.id,
            path="设定/人物.md",
            content="# 人物\n\n林渊\n\n新增：夜雨观察力极强。",
            base_version=target.version,
            expected_document_ref=target.document_ref,
            expected_binding_version=_build_entry_binding_version(target),
            active_buffer_state=_build_trusted_active_buffer_state(
                base_version=target.version,
                content=current_content,
            ),
            allowed_target_document_refs=(target.document_ref,),
            require_trusted_buffer_state=True,
            run_audit_id="run-audit-6",
        )
    )
    file_store.save_project_document(project.id, "设定/人物.md", "# 人物\n\n被外部绕过修改")
    tampered = next(
        item
        for item in asyncio.run(capability_service.list_document_catalog(async_db(db), project.id))
        if item.path == "设定/人物.md"
    )

    try:
        asyncio.run(
            capability_service.write_document(
                async_db(db),
                project.id,
                path="设定/人物.md",
                content="# 人物\n\n再次写回",
                base_version=tampered.version,
                expected_document_ref=tampered.document_ref,
                expected_binding_version=_build_entry_binding_version(tampered),
                active_buffer_state=_build_trusted_active_buffer_state(
                    base_version=tampered.version,
                    content="# 人物\n\n被外部绕过修改",
                ),
                allowed_target_document_refs=(tampered.document_ref,),
                require_trusted_buffer_state=True,
                run_audit_id="run-audit-7",
            )
        )
    except ProjectDocumentMutationError as exc:
        assert exc.code == "revision_state_mismatch"
    else:
        raise AssertionError("expected revision_state_mismatch")


def test_project_document_binding_version_includes_source_and_mutability_metadata() -> None:
    file_binding = _build_binding_version(
        "设定/人物.md",
        "project_file:1",
        source="file",
        document_kind="markdown",
        writable=True,
    )
    readonly_binding = _build_binding_version(
        "设定/人物.md",
        "project_file:1",
        source="file",
        document_kind="markdown",
        writable=False,
    )
    json_binding = _build_binding_version(
        "设定/人物.md",
        "project_file:1",
        source="file",
        document_kind="json",
        writable=True,
    )

    assert file_binding != readonly_binding
    assert file_binding != json_binding


def _build_entry_binding_version(entry) -> str:
    return _build_binding_version(
        entry.path,
        entry.document_ref,
        source=entry.source,
        document_kind=entry.document_kind,
        writable=entry.writable,
    )


def _build_binding_version(
    path: str,
    document_ref: str,
    *,
    source: str,
    document_kind: str,
    writable: bool,
) -> str:
    payload = json.dumps(
        {
            "document_ref": document_ref,
            "document_kind": document_kind,
            "path": path,
            "source": source,
            "writable": writable,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_catalog_record(
    *,
    content_state: str = "ready",
    document_kind: str = "markdown",
    document_ref: str = "project_file:1",
    mime_type: str = "text/markdown",
    path: str = "设定/人物.md",
    resource_uri: str = "project-document://project/project_file%3A1",
    schema_id: str | None = "project.characters",
    source: str = "file",
    title: str = "人物",
    version: str = "sha256:1",
    writable: bool = True,
):
    return SimpleNamespace(
        content_state=content_state,
        document_kind=document_kind,
        document_ref=document_ref,
        mime_type=mime_type,
        path=path,
        resource_uri=resource_uri,
        schema_id=schema_id,
        source=source,
        title=title,
        version=version,
        writable=writable,
    )
