from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.project.models import Project
from app.modules.project.schemas import ProjectSetting
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import (
    ProjectSettingSnapshotDTO,
    ProjectSettingUpdateDTO,
    SettingCompletenessIssueDTO,
    SettingCompletenessResultDTO,
)

ASSET_TYPES_TO_STALE = frozenset({"outline", "opening_plan", "chapter"})
CHAPTER_TASK_STALE_STATUS = "stale"


class ProjectService:
    def require_project(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
        include_deleted: bool = False,
    ) -> Project:
        return self._require_project(
            db,
            project_id,
            owner_id=owner_id,
            include_deleted=include_deleted,
        )

    def update_project_setting(
        self,
        db: Session,
        project_id: uuid.UUID,
        payload: ProjectSettingUpdateDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectSettingSnapshotDTO:
        project = self._require_project(db, project_id, owner_id=owner_id)
        setting_dict = payload.project_setting.model_dump(exclude_none=True)
        setting_changed = project.project_setting != setting_dict
        project.project_setting = setting_dict
        if setting_changed:
            self._mark_related_content_stale(project)
            self._mark_chapter_tasks_stale(db, project.id)
        db.add(project)
        db.commit()
        db.refresh(project)
        return self._to_snapshot(project)

    def check_setting_completeness(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> SettingCompletenessResultDTO:
        project = self._require_project(db, project_id, owner_id=owner_id)
        return self._evaluate_setting(project)

    def ensure_setting_allows_preparation(
        self,
        project: Project,
    ) -> SettingCompletenessResultDTO:
        result = self._evaluate_setting(project)
        if result.status == "blocked":
            raise BusinessRuleError(self._format_blocked_message(result.issues))
        return result

    def _require_project(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
        include_deleted: bool = False,
    ) -> Project:
        query = db.query(Project).filter(Project.id == project_id)
        if owner_id is not None:
            query = query.filter(Project.owner_id == owner_id)
        if not include_deleted:
            query = query.filter(Project.deleted_at.is_(None))
        project = query.one_or_none()
        if project is None:
            raise NotFoundError(f"Project not found: {project_id}")
        return project

    def _collect_issues(
        self,
        setting: ProjectSetting,
    ) -> list[SettingCompletenessIssueDTO]:
        issues: list[SettingCompletenessIssueDTO] = []
        self._append_required_issues(issues, setting)
        self._append_optional_issues(issues, setting)
        return issues

    def _append_required_issues(
        self,
        issues: list[SettingCompletenessIssueDTO],
        setting: ProjectSetting,
    ) -> None:
        protagonist = setting.protagonist
        world_setting = setting.world_setting
        has_protagonist_entry = bool(
            protagonist and (protagonist.identity or protagonist.initial_situation)
        )
        has_world_baseline = bool(
            world_setting
            and (
                world_setting.era_baseline
                or world_setting.world_rules
                or world_setting.power_system
                or world_setting.key_locations
            )
        )
        if not setting.genre:
            issues.append(self._issue("genre", "blocked", "缺少题材/类型"))
        if not has_protagonist_entry:
            issues.append(
                self._issue(
                    "protagonist.identity",
                    "blocked",
                    "主角核心信息缺失，至少需要身份或初始处境",
                )
            )
        if not (protagonist and protagonist.goal):
            issues.append(
                self._issue("protagonist.goal", "blocked", "缺少主角核心目标")
            )
        if not setting.core_conflict:
            issues.append(
                self._issue("core_conflict", "blocked", "缺少核心冲突")
            )
        if not has_world_baseline:
            issues.append(
                self._issue(
                    "world_setting",
                    "blocked",
                    "缺少世界基线，至少需要时代背景、世界规则、力量体系或关键地点",
                )
            )

    def _append_optional_issues(
        self,
        issues: list[SettingCompletenessIssueDTO],
        setting: ProjectSetting,
    ) -> None:
        scale = setting.scale
        has_scale = bool(scale and (scale.target_words or scale.target_chapters))
        if not setting.tone:
            issues.append(self._issue("tone", "warning", "缺少基调/风格"))
        if not has_scale:
            issues.append(
                self._issue(
                    "scale",
                    "warning",
                    "缺少目标篇幅或章节规模，后续预算与规划精度会下降",
                )
            )

    def _mark_related_content_stale(self, project: Project) -> None:
        for content in project.contents:
            if content.content_type not in ASSET_TYPES_TO_STALE:
                continue
            if content.status == "approved":
                content.status = "stale"

    def _mark_chapter_tasks_stale(
        self,
        db: Session,
        project_id: uuid.UUID,
    ) -> None:
        tasks = (
            db.query(ChapterTask)
            .filter(ChapterTask.project_id == project_id)
            .all()
        )
        for task in tasks:
            if task.status == CHAPTER_TASK_STALE_STATUS:
                continue
            task.status = CHAPTER_TASK_STALE_STATUS

    def _evaluate_setting(self, project: Project) -> SettingCompletenessResultDTO:
        setting = ProjectSetting.model_validate(project.project_setting or {})
        issues = self._collect_issues(setting)
        status = self._resolve_status(issues)
        return SettingCompletenessResultDTO(status=status, issues=issues)

    def _resolve_status(
        self,
        issues: list[SettingCompletenessIssueDTO],
    ) -> str:
        if any(issue.level == "blocked" for issue in issues):
            return "blocked"
        if issues:
            return "warning"
        return "ready"

    def _to_snapshot(self, project: Project) -> ProjectSettingSnapshotDTO:
        setting = None
        if project.project_setting is not None:
            setting = ProjectSetting.model_validate(project.project_setting)
        return ProjectSettingSnapshotDTO(
            project_id=project.id,
            genre=project.genre,
            target_words=project.target_words,
            status=project.status,
            project_setting=setting,
        )

    def _issue(
        self,
        field: str,
        level: str,
        message: str,
    ) -> SettingCompletenessIssueDTO:
        return SettingCompletenessIssueDTO(field=field, level=level, message=message)

    def _format_blocked_message(
        self,
        issues: list[SettingCompletenessIssueDTO],
    ) -> str:
        blocked_messages = [
            issue.message
            for issue in issues
            if issue.level == "blocked"
        ]
        unique_messages = list(dict.fromkeys(blocked_messages))
        details = "；".join(unique_messages)
        return f"项目设定未完成，无法继续：{details}"
