from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.project.models import Project
from app.modules.project.schemas import ProjectSetting
from app.shared.runtime.errors import BusinessRuleError

from .dto import (
    ProjectSettingSnapshotDTO,
    SettingCompletenessIssueDTO,
    SettingCompletenessResultDTO,
)

ASSET_TYPES_TO_STALE = frozenset({"outline", "opening_plan", "chapter"})
CHAPTER_TASK_STALE_STATUS = "stale"


def build_project_statement(
    project_id: uuid.UUID,
    *,
    owner_id: uuid.UUID | None,
    include_deleted: bool,
    load_contents: bool = False,
    load_template: bool = False,
):
    statement = select(Project).where(Project.id == project_id)
    if owner_id is not None:
        statement = statement.where(Project.owner_id == owner_id)
    if not include_deleted:
        statement = statement.where(Project.deleted_at.is_(None))
    if load_contents:
        statement = statement.options(selectinload(Project.contents))
    if load_template:
        statement = statement.options(selectinload(Project.template))
    return statement


def ensure_setting_allows_preparation(project: Project) -> SettingCompletenessResultDTO:
    result = evaluate_setting(project)
    if result.status == "blocked":
        raise BusinessRuleError(format_blocked_message(result.issues))
    return result


def evaluate_setting(project: Project) -> SettingCompletenessResultDTO:
    setting = ProjectSetting.model_validate(project.project_setting or {})
    issues = collect_setting_issues(setting)
    return SettingCompletenessResultDTO(status=resolve_status(issues), issues=issues)


def to_snapshot(project: Project) -> ProjectSettingSnapshotDTO:
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


def mark_related_content_stale(project: Project) -> None:
    for content in project.contents:
        if content.content_type not in ASSET_TYPES_TO_STALE:
            continue
        if content.status == "approved":
            content.status = "stale"


def collect_setting_issues(setting: ProjectSetting) -> list[SettingCompletenessIssueDTO]:
    issues = build_required_issues(setting)
    issues.extend(build_optional_issues(setting))
    return issues


def build_required_issues(setting: ProjectSetting) -> list[SettingCompletenessIssueDTO]:
    issues: list[SettingCompletenessIssueDTO] = []
    protagonist = setting.protagonist
    world_setting = setting.world_setting
    has_protagonist_entry = bool(protagonist and (protagonist.identity or protagonist.initial_situation))
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
        issues.append(issue("genre", "blocked", "缺少题材/类型"))
    if not has_protagonist_entry:
        issues.append(
            issue(
                "protagonist.identity",
                "blocked",
                "主角核心信息缺失，至少需要身份或初始处境",
            )
        )
    if not (protagonist and protagonist.goal):
        issues.append(issue("protagonist.goal", "blocked", "缺少主角核心目标"))
    if not setting.core_conflict:
        issues.append(issue("core_conflict", "blocked", "缺少核心冲突"))
    if not has_world_baseline:
        issues.append(
            issue(
                "world_setting",
                "blocked",
                "缺少世界基线，至少需要时代背景、世界规则、力量体系或关键地点",
            )
        )
    return issues


def build_optional_issues(setting: ProjectSetting) -> list[SettingCompletenessIssueDTO]:
    issues: list[SettingCompletenessIssueDTO] = []
    scale = setting.scale
    has_scale = bool(scale and (scale.target_words or scale.target_chapters))
    if not setting.tone:
        issues.append(issue("tone", "warning", "缺少基调/风格"))
    if not has_scale:
        issues.append(
            issue(
                "scale",
                "warning",
                "缺少目标篇幅或章节规模，后续预算与规划精度会下降",
            )
        )
    return issues


def resolve_status(issues: list[SettingCompletenessIssueDTO]) -> str:
    if any(item.level == "blocked" for item in issues):
        return "blocked"
    if issues:
        return "warning"
    return "ready"


def format_blocked_message(issues: list[SettingCompletenessIssueDTO]) -> str:
    blocked_messages = [item.message for item in issues if item.level == "blocked"]
    details = "；".join(dict.fromkeys(blocked_messages))
    return f"项目设定未完成，无法继续：{details}"


def issue(
    field: str,
    level: str,
    message: str,
) -> SettingCompletenessIssueDTO:
    return SettingCompletenessIssueDTO(field=field, level=level, message=message)
