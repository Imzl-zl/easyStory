from __future__ import annotations

from datetime import UTC, datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content, ContentVersion
from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.modules.workflow.service.snapshot_support import workflow_to_summary_dto
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import (
    PreparationAssetStatusDTO,
    PreparationChapterTaskCountsDTO,
    PreparationChapterTaskStatusDTO,
    PreparationNextStep,
    ProjectDocumentEntryCreateDTO,
    ProjectDocumentEntryDTO,
    ProjectDocumentEntryDeleteResultDTO,
    ProjectDocumentEntryRenameDTO,
    ProjectDocumentDTO,
    ProjectDocumentSaveDTO,
    ProjectDocumentTreeNodeDTO,
    ProjectPreparationStatusDTO,
    ProjectSettingSnapshotDTO,
    ProjectSettingUpdateDTO,
    SettingCompletenessResultDTO,
)
from .project_document_support import (
    OPENING_PLAN_DOCUMENT_PATH,
    OUTLINE_DOCUMENT_PATH,
    PROJECT_DOCUMENT_TEMPLATE_VERSION,
    build_default_project_document_template_files,
    is_canonical_project_document_path,
    is_creatable_project_document_file_path,
    is_fixed_project_document_folder_path,
    is_mutable_project_document_file_path,
    is_mutable_project_document_folder_path,
    is_supported_file_project_document_path,
    is_visible_project_document_tree_file_path,
    list_default_project_document_template_folders,
    parse_chapter_number_from_document_path,
)
from .project_service_support import (
    CHAPTER_TASK_STALE_STATUS,
    build_setting_impact_summary,
    build_project_statement,
    count_chapter_tasks,
    current_version,
    ensure_setting_allows_preparation,
    evaluate_setting,
    mark_related_content_stale,
    resolve_asset_step_status,
    resolve_chapter_task_step_status,
    to_snapshot,
)

if TYPE_CHECKING:
    from app.modules.project.infrastructure import (
        ProjectDocumentEntryRecord,
        ProjectDocumentFileStore,
        ProjectDocumentIdentityStore,
        ProjectDocumentTreeNodeRecord,
    )


class ProjectService:
    def __init__(
        self,
        *,
        document_file_store: "ProjectDocumentFileStore | None" = None,
        document_identity_store: "ProjectDocumentIdentityStore | None" = None,
    ) -> None:
        self.document_file_store = document_file_store
        self.document_identity_store = document_identity_store

    async def require_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        load_contents: bool = False,
        load_template: bool = False,
    ) -> Project:
        project = await db.scalar(
            build_project_statement(
                project_id,
                owner_id=owner_id,
                include_deleted=include_deleted,
                load_contents=load_contents,
                load_template=load_template,
            )
        )
        if project is None:
            raise NotFoundError(f"Project not found: {project_id}")
        return project

    async def update_project_setting(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ProjectSettingUpdateDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectSettingSnapshotDTO:
        project = await self.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_contents=True,
        )
        setting_dict = payload.project_setting.model_dump(exclude_none=True)
        if project.project_setting == setting_dict:
            return to_snapshot(project)
        project.project_setting = setting_dict
        content_impacts = mark_related_content_stale(project)
        stale_chapter_task_count = await self._mark_chapter_tasks_stale(db, project.id)
        impact = build_setting_impact_summary(
            content_impacts,
            stale_chapter_task_count=stale_chapter_task_count,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return to_snapshot(project, impact=impact)

    async def get_project_document(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        document_path: str,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        if not is_canonical_project_document_path(document_path):
            file_store = self._require_document_file_store()
            record = file_store.find_project_document(project.id, document_path)
            if record is None:
                raise NotFoundError("目标文件不存在")
            return ProjectDocumentDTO(
                project_id=project.id,
                path=document_path,
                content=record.content,
                source="file",
                updated_at=record.updated_at,
            )
        content, source = await self._load_project_document_seed(db, project, document_path)
        return ProjectDocumentDTO(
            project_id=project.id,
            path=document_path,
            content=content,
            source=source,
            updated_at=None,
        )

    async def save_project_document(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        document_path: str,
        payload: ProjectDocumentSaveDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        if self.document_file_store is None:
            raise RuntimeError("Project document file store is not configured")
        if is_canonical_project_document_path(document_path):
            raise BusinessRuleError("该文稿属于正式内容真值，请通过大纲或正文保存链路更新")
        record = self.document_file_store.save_project_document(project.id, document_path, payload.content)
        self._resolve_document_ref(project.id, document_path)
        return ProjectDocumentDTO(
            project_id=project.id,
            path=document_path,
            content=record.content,
            source="file",
            updated_at=record.updated_at,
        )

    async def list_project_document_tree(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> list[ProjectDocumentTreeNodeDTO]:
        self._require_document_file_store()
        project = await self.require_project(db, project_id, owner_id=owner_id)
        nodes = self.document_file_store.list_project_document_tree(project.id)
        return [
            self._to_project_document_tree_node_dto(node)
            for node in nodes
            if self._should_include_tree_node(node)
        ]

    async def create_project_document_entry(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ProjectDocumentEntryCreateDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentEntryDTO:
        file_store = self._require_document_file_store()
        project = await self.require_project(db, project_id, owner_id=owner_id)
        if payload.kind == "file":
            if not is_creatable_project_document_file_path(payload.path):
                raise BusinessRuleError("正文下只能新建章节文稿，其他区域只能新建自定义 .md 或 .json 文稿")
            chapter_number = parse_chapter_number_from_document_path(payload.path)
            if chapter_number is not None:
                self.ensure_setting_allows_preparation(project)
                await self._require_chapter_preparation_assets_ready(db, project.id)
                record = await self._create_project_chapter_document_entry(
                    db,
                    project,
                    document_path=payload.path,
                    chapter_number=chapter_number,
                )
                return self._to_project_document_entry_dto(record)
            record = file_store.create_project_document_file(project.id, payload.path)
            self._resolve_document_ref(project.id, payload.path)
            return self._to_project_document_entry_dto(record)
        if not is_mutable_project_document_folder_path(payload.path):
            raise BusinessRuleError("固定目录不支持新增子目录")
        record = file_store.create_project_document_folder(project.id, payload.path)
        return self._to_project_document_entry_dto(record)

    async def rename_project_document_entry(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ProjectDocumentEntryRenameDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentEntryDTO:
        file_store = self._require_document_file_store()
        project = await self.require_project(db, project_id, owner_id=owner_id)
        if is_fixed_project_document_folder_path(payload.path):
            raise BusinessRuleError("固定目录不支持重命名")
        source_entry = file_store.find_project_document_entry(project.id, payload.path)
        if source_entry is None:
            raise BusinessRuleError("目标文稿不存在")
        if payload.path == payload.next_path:
            raise BusinessRuleError("新路径不能和原路径相同")
        self._validate_mutable_project_document_entry(source_entry)
        self._validate_target_project_document_path(payload.next_path, source_entry.node_type)
        record = file_store.rename_project_document_entry(
            project.id,
            payload.path,
            source_entry.node_type,
            payload.next_path,
        )
        self._rename_document_ref(project.id, source_path=payload.path, target_path=payload.next_path)
        return self._to_project_document_entry_dto(record)

    async def delete_project_document_entry(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        document_path: str,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentEntryDeleteResultDTO:
        file_store = self._require_document_file_store()
        project = await self.require_project(db, project_id, owner_id=owner_id)
        if is_fixed_project_document_folder_path(document_path):
            raise BusinessRuleError("固定目录不支持删除")
        source_entry = file_store.find_project_document_entry(project.id, document_path)
        if source_entry is None:
            raise BusinessRuleError("目标文稿不存在")
        self._validate_mutable_project_document_entry(source_entry)
        if source_entry.node_type == "folder":
            self._validate_project_document_folder_delete(project.id, source_entry.path)
        deleted_entry = file_store.delete_project_document_entry(project.id, document_path)
        self._delete_document_ref(project.id, document_path)
        return ProjectDocumentEntryDeleteResultDTO(
            node_type=deleted_entry.node_type,
            path=deleted_entry.path,
        )

    def _require_document_file_store(self) -> "ProjectDocumentFileStore":
        if self.document_file_store is None:
            raise RuntimeError("Project document file store is not configured")
        return self.document_file_store

    def _resolve_document_ref(self, project_id: uuid.UUID, document_path: str) -> str | None:
        if self.document_identity_store is None or is_canonical_project_document_path(document_path):
            return None
        return self.document_identity_store.resolve_document_ref(project_id, path=document_path)

    def _rename_document_ref(
        self,
        project_id: uuid.UUID,
        *,
        source_path: str,
        target_path: str,
    ) -> None:
        if self.document_identity_store is None:
            return
        self.document_identity_store.rename_document_ref(
            project_id,
            source_path=source_path,
            target_path=target_path,
        )

    def _delete_document_ref(self, project_id: uuid.UUID, document_path: str) -> None:
        if self.document_identity_store is None or is_canonical_project_document_path(document_path):
            return
        self.document_identity_store.delete_document_ref(project_id, path=document_path)

    def _should_include_tree_node(self, node: "ProjectDocumentTreeNodeRecord") -> bool:
        if not is_supported_file_project_document_path(node.path):
            return False
        if node.node_type == "file":
            return is_visible_project_document_tree_file_path(node.path)
        children = tuple(child for child in node.children if self._should_include_tree_node(child))
        return (
            len(children) > 0
            or is_mutable_project_document_folder_path(node.path)
            or is_fixed_project_document_folder_path(node.path)
        )

    def _to_project_document_tree_node_dto(
        self,
        node: "ProjectDocumentTreeNodeRecord",
    ) -> ProjectDocumentTreeNodeDTO:
        children = [
            self._to_project_document_tree_node_dto(child)
            for child in node.children
            if self._should_include_tree_node(child)
        ]
        return ProjectDocumentTreeNodeDTO(
            children=children,
            label=node.label,
            node_type=node.node_type,
            path=node.path,
        )

    def _to_project_document_entry_dto(
        self,
        entry: "ProjectDocumentEntryRecord",
    ) -> ProjectDocumentEntryDTO:
        return ProjectDocumentEntryDTO(
            label=entry.label,
            node_type=entry.node_type,
            path=entry.path,
        )

    def _validate_mutable_project_document_entry(
        self,
        entry: "ProjectDocumentEntryRecord",
    ) -> None:
        if entry.node_type == "file":
            if not is_mutable_project_document_file_path(entry.path):
                raise BusinessRuleError("固定文稿不支持重命名或删除")
            return
        if not is_mutable_project_document_folder_path(entry.path):
            raise BusinessRuleError("固定目录不支持重命名或删除")

    def _validate_target_project_document_path(
        self,
        document_path: str,
        node_type: str,
    ) -> None:
        if node_type == "file":
            if not is_mutable_project_document_file_path(document_path):
                raise BusinessRuleError("只能重命名到正文之外的自定义 .md 或 .json 文稿")
            return
        if not is_mutable_project_document_folder_path(document_path):
            raise BusinessRuleError("只能重命名到正文之外的自定义目录")

    async def _create_project_chapter_document_entry(
        self,
        db: AsyncSession,
        project: Project,
        *,
        document_path: str,
        chapter_number: int,
    ) -> "ProjectDocumentEntryRecord":
        file_store = self._require_document_file_store()
        existing_chapter = await db.scalar(
            select(Content.id).where(
                Content.project_id == project.id,
                Content.content_type == "chapter",
                Content.chapter_number == chapter_number,
            )
        )
        if existing_chapter is not None:
            raise BusinessRuleError("该章节已经存在")
        if file_store.find_project_document_entry(project.id, document_path) is not None:
            raise BusinessRuleError("文稿已存在")

        now = datetime.now(UTC)
        title = f"第{chapter_number:03d}章"
        chapter = Content(
            project_id=project.id,
            parent_id=None,
            content_type="chapter",
            title=title,
            chapter_number=chapter_number,
            order_index=chapter_number,
            status="draft",
            last_edited_at=now,
            metadata_=None,
            versions=[
                ContentVersion(
                    version_number=1,
                    content_text=f"# {title}\n\n",
                    created_by="user",
                    change_source="user_edit",
                    is_current=True,
                    is_best=False,
                    word_count=len(title),
                )
            ],
        )
        db.add(chapter)
        created_placeholder = False
        try:
            await db.flush()
            record = file_store.create_project_document_file(project.id, document_path)
            created_placeholder = True
            await db.commit()
            return record
        except Exception:
            await db.rollback()
            if created_placeholder:
                try:
                    file_store.delete_project_document_entry(project.id, document_path)
                except Exception:
                    pass
            raise

    def _validate_project_document_folder_delete(
        self,
        project_id: uuid.UUID,
        folder_path: str,
    ) -> None:
        file_store = self._require_document_file_store()
        existing_tree = file_store.list_project_document_tree(project_id)
        folder_node = next((node for node in existing_tree if node.path == folder_path), None)
        if folder_node is None:
            folder_node = self._find_tree_node(existing_tree, folder_path)
        if folder_node is None:
            return
        if self._contains_chapter_document_path(folder_node):
            raise BusinessRuleError("包含章节文稿的正文目录暂不支持直接删除")

    def _find_tree_node(
        self,
        nodes: list["ProjectDocumentTreeNodeRecord"],
        target_path: str,
    ) -> "ProjectDocumentTreeNodeRecord | None":
        for node in nodes:
            if node.path == target_path:
                return node
            if node.children:
                found = self._find_tree_node(list(node.children), target_path)
                if found is not None:
                    return found
        return None

    def _contains_chapter_document_path(self, node: "ProjectDocumentTreeNodeRecord") -> bool:
        if node.node_type == "file":
            return parse_chapter_number_from_document_path(node.path) is not None
        return any(self._contains_chapter_document_path(child) for child in node.children)

    async def _require_chapter_preparation_assets_ready(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        for content_type in ("outline", "opening_plan"):
            asset = await db.scalar(
                select(Content.status).where(
                    Content.project_id == project_id,
                    Content.content_type == content_type,
                )
            )
            if asset != "approved":
                raise BusinessRuleError(f"{content_type} 必须先确认后才能继续")

    async def ensure_project_document_template(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> None:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        file_store = self._require_document_file_store()
        current_version = file_store.get_project_document_template_version(project.id)
        if current_version >= PROJECT_DOCUMENT_TEMPLATE_VERSION:
            return
        if current_version != 0:
            raise BusinessRuleError("检测到旧版文稿模板，请先执行显式模板迁移")
        template_files = build_default_project_document_template_files(
            project_name=project.name,
            project_status=project.status,
            setting_payload=project.project_setting,
            chapters=(),
        )
        file_store.bootstrap_project_document_template(
            project.id,
            folder_paths=list_default_project_document_template_folders(),
            file_entries=tuple((item.path, item.content) for item in template_files),
            template_version=PROJECT_DOCUMENT_TEMPLATE_VERSION,
        )

    async def check_setting_completeness(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> SettingCompletenessResultDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        return evaluate_setting(project)

    def ensure_setting_allows_preparation(self, project: Project) -> SettingCompletenessResultDTO:
        return ensure_setting_allows_preparation(project)

    async def get_preparation_status(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectPreparationStatusDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        setting = evaluate_setting(project)
        outline = await self._get_asset_status(db, project.id, "outline")
        opening_plan = await self._get_asset_status(db, project.id, "opening_plan")
        active_workflow = await self._find_active_workflow(db, project.id)
        relevant_workflow = active_workflow or await self._find_latest_workflow(db, project.id)
        chapter_tasks = await self._get_chapter_task_status(
            db,
            relevant_workflow.id if relevant_workflow is not None else None,
        )
        can_start_workflow = self._can_start_workflow(setting, outline, opening_plan, active_workflow)
        next_step, next_step_detail = self._resolve_next_step(
            setting,
            outline,
            opening_plan,
            chapter_tasks,
            active_workflow,
        )
        return ProjectPreparationStatusDTO(
            project_id=project.id,
            setting=setting,
            outline=outline,
            opening_plan=opening_plan,
            chapter_tasks=chapter_tasks,
            active_workflow=(
                workflow_to_summary_dto(active_workflow) if active_workflow is not None else None
            ),
            can_start_workflow=can_start_workflow,
            next_step=next_step,
            next_step_detail=next_step_detail,
        )

    async def _mark_chapter_tasks_stale(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> int:
        tasks = (await db.scalars(select(ChapterTask).where(ChapterTask.project_id == project_id))).all()
        updated_count = 0
        for task in tasks:
            if task.status == CHAPTER_TASK_STALE_STATUS:
                continue
            task.status = CHAPTER_TASK_STALE_STATUS
            updated_count += 1
        return updated_count

    async def _get_asset_status(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_type: str,
    ) -> PreparationAssetStatusDTO:
        content = await db.scalar(
            select(Content)
            .options(selectinload(Content.versions))
            .where(
                Content.project_id == project_id,
                Content.content_type == content_type,
            )
        )
        if content is None:
            return PreparationAssetStatusDTO(
                content_id=None,
                step_status="not_started",
                content_status=None,
                version_number=None,
                has_content=False,
                updated_at=None,
            )
        version = current_version(content)
        has_content = bool(version and version.content_text.strip())
        return PreparationAssetStatusDTO(
            content_id=content.id,
            step_status=resolve_asset_step_status(content, has_content),
            content_status=content.status,
            version_number=version.version_number if version is not None else None,
            has_content=has_content,
            updated_at=content.updated_at,
        )

    async def _find_active_workflow(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        return await db.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.project_id == project_id,
                WorkflowExecution.status.in_(("created", "running", "paused")),
            )
        )

    async def _find_latest_workflow(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        return await db.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.project_id == project_id)
            .order_by(
                WorkflowExecution.updated_at.desc(),
                WorkflowExecution.completed_at.desc().nulls_last(),
                WorkflowExecution.started_at.desc().nulls_last(),
                WorkflowExecution.created_at.desc(),
                WorkflowExecution.id.desc(),
            )
            .limit(1)
        )

    async def _get_chapter_task_status(
        self,
        db: AsyncSession,
        workflow_execution_id: uuid.UUID | None,
    ) -> PreparationChapterTaskStatusDTO:
        if workflow_execution_id is None:
            return PreparationChapterTaskStatusDTO(
                workflow_execution_id=None,
                step_status="not_started",
                total=0,
                counts=PreparationChapterTaskCountsDTO(),
            )
        tasks = (
            await db.scalars(
                select(ChapterTask).where(ChapterTask.workflow_execution_id == workflow_execution_id)
            )
        ).all()
        counts = count_chapter_tasks(tasks)
        return PreparationChapterTaskStatusDTO(
            workflow_execution_id=workflow_execution_id,
            step_status=resolve_chapter_task_step_status(counts),
            total=len(tasks),
            counts=counts,
        )

    async def _load_project_document_seed(
        self,
        db: AsyncSession,
        project: Project,
        document_path: str,
    ) -> tuple[str, str]:
        if document_path == OUTLINE_DOCUMENT_PATH:
            return await self._load_story_asset_seed(db, project.id, "outline"), "outline"
        if document_path == OPENING_PLAN_DOCUMENT_PATH:
            return await self._load_story_asset_seed(db, project.id, "opening_plan"), "opening_plan"
        chapter_number = parse_chapter_number_from_document_path(document_path)
        if chapter_number is not None:
            return await self._load_chapter_seed(db, project.id, chapter_number), "chapter"
        raise NotFoundError("目标文稿不存在")

    async def _load_story_asset_seed(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_type: str,
    ) -> str:
        content = await db.scalar(
            select(Content)
            .options(selectinload(Content.versions))
            .where(Content.project_id == project_id, Content.content_type == content_type)
        )
        version = current_version(content) if content is not None else None
        return version.content_text if version is not None else ""

    async def _load_chapter_seed(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
    ) -> str:
        content = await db.scalar(
            select(Content)
            .options(selectinload(Content.versions))
            .where(
                Content.project_id == project_id,
                Content.content_type == "chapter",
                Content.chapter_number == chapter_number,
            )
        )
        version = current_version(content) if content is not None else None
        return version.content_text if version is not None else ""

    def _can_start_workflow(
        self,
        setting: SettingCompletenessResultDTO,
        outline: PreparationAssetStatusDTO,
        opening_plan: PreparationAssetStatusDTO,
        active_workflow: WorkflowExecution | None,
    ) -> bool:
        del setting
        return (
            outline.step_status == "approved"
            and opening_plan.step_status == "approved"
            and active_workflow is None
        )

    def _resolve_next_step(
        self,
        setting: SettingCompletenessResultDTO,
        outline: PreparationAssetStatusDTO,
        opening_plan: PreparationAssetStatusDTO,
        chapter_tasks: PreparationChapterTaskStatusDTO,
        active_workflow: WorkflowExecution | None,
    ) -> tuple[PreparationNextStep, str]:
        if outline.step_status != "approved":
            return "outline", "需要先生成并确认大纲"
        if opening_plan.step_status != "approved":
            return "opening_plan", "需要先生成并确认开篇设计"
        if chapter_tasks.step_status == "stale" and active_workflow is not None:
            return "chapter_tasks", "当前章节计划已失效，需要在现有工作流中重建章节任务"
        if active_workflow is not None:
            return "workflow", "当前已有活跃工作流，可继续推进章节任务或正文生成"
        if chapter_tasks.step_status == "completed":
            return "chapter", "章节计划已就绪，可继续推进正文生成与确认"
        if setting.issues:
            return "workflow", "结构化摘要还有可补充项，但这不会阻塞继续生成大纲、开篇或正文。"
        return "workflow", "前置资产已就绪，可以启动工作流"
