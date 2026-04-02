from __future__ import annotations

from collections import Counter
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content
from app.modules.project.models import Project
from app.modules.project.schemas import ProjectSetting

from .dto import (
    PreparationChapterTaskCountsDTO,
    ProjectSettingImpactItemDTO,
    ProjectSettingImpactSummaryDTO,
    ProjectSettingSnapshotDTO,
    SettingCompletenessIssueDTO,
    SettingCompletenessResultDTO,
)

ASSET_TYPES_TO_STALE = frozenset({"outline", "opening_plan", "chapter"})
CHAPTER_TASK_STALE_STATUS = "stale"
SETTING_IMPACT_ORDER = ("outline", "opening_plan", "chapter")


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
    return evaluate_setting(project)


def evaluate_setting(project: Project) -> SettingCompletenessResultDTO:
    setting = ProjectSetting.model_validate(project.project_setting or {})
    return evaluate_project_setting(setting)


def evaluate_project_setting(setting: ProjectSetting) -> SettingCompletenessResultDTO:
    issues = collect_setting_issues(setting)
    return SettingCompletenessResultDTO(status=resolve_status(issues), issues=issues)


def to_snapshot(
    project: Project,
    *,
    impact: ProjectSettingImpactSummaryDTO | None = None,
) -> ProjectSettingSnapshotDTO:
    setting = None
    if project.project_setting is not None:
        setting = ProjectSetting.model_validate(project.project_setting)
    return ProjectSettingSnapshotDTO(
        project_id=project.id,
        genre=project.genre,
        target_words=project.target_words,
        status=project.status,
        project_setting=setting,
        impact=impact or ProjectSettingImpactSummaryDTO(),
    )


def mark_related_content_stale(project: Project) -> list[ProjectSettingImpactItemDTO]:
    impacted_contents: list[Content] = []
    for content in project.contents:
        if content.content_type not in ASSET_TYPES_TO_STALE:
            continue
        if content.status == "approved":
            content.status = "stale"
            impacted_contents.append(content)
    return build_content_stale_impacts(impacted_contents)


def build_content_stale_impacts(contents: list[Content]) -> list[ProjectSettingImpactItemDTO]:
    counts = Counter(content.content_type for content in contents)
    impacts: list[ProjectSettingImpactItemDTO] = []
    for target in SETTING_IMPACT_ORDER:
        count = counts.get(target, 0)
        if count > 0:
            impacts.append(build_setting_impact_item(target, count))
    return impacts


def build_setting_impact_summary(
    content_impacts: list[ProjectSettingImpactItemDTO],
    *,
    stale_chapter_task_count: int,
) -> ProjectSettingImpactSummaryDTO:
    items = list(content_impacts)
    if stale_chapter_task_count > 0:
        items.append(build_setting_impact_item("chapter_tasks", stale_chapter_task_count))
    return ProjectSettingImpactSummaryDTO(
        has_impact=bool(items),
        total_affected_entries=sum(item.count for item in items),
        items=items,
    )


def build_setting_impact_item(
    target: str,
    count: int,
) -> ProjectSettingImpactItemDTO:
    return ProjectSettingImpactItemDTO(
        target=target,
        action="mark_stale",
        count=count,
        message=format_setting_impact_message(target, count),
    )


def format_setting_impact_message(target: str, count: int) -> str:
    if target == "outline":
        return "已确认大纲将标记为 stale，需要重新确认。"
    if target == "opening_plan":
        return "已确认开篇设计将标记为 stale，需要在大纲稳定后重新确认。"
    if target == "chapter":
        return f"{count} 个已确认章节将标记为 stale，需要按范围复核正文。"
    return f"{count} 个章节任务将标记为 stale，需要重新执行章节拆分。"


def resolve_asset_step_status(
    content: Content,
    has_content: bool,
) -> str:
    if content.status == "approved":
        return "approved"
    if content.status == "stale":
        return "stale"
    if content.status == "archived":
        return "archived"
    if not has_content:
        return "not_started"
    return "draft"


def count_chapter_tasks(tasks) -> PreparationChapterTaskCountsDTO:
    counts = PreparationChapterTaskCountsDTO()
    for task in tasks:
        if task.status == "pending":
            counts.pending += 1
        elif task.status == "generating":
            counts.generating += 1
        elif task.status == "completed":
            counts.completed += 1
        elif task.status == "failed":
            counts.failed += 1
        elif task.status == "skipped":
            counts.skipped += 1
        elif task.status == "stale":
            counts.stale += 1
        elif task.status == "interrupted":
            counts.interrupted += 1
    return counts


def resolve_chapter_task_step_status(
    counts: PreparationChapterTaskCountsDTO,
) -> str:
    total = sum(counts.model_dump().values())
    if total == 0:
        return "not_started"
    if counts.stale:
        return "stale"
    if counts.failed:
        return "failed"
    if counts.interrupted:
        return "interrupted"
    if counts.generating:
        return "generating"
    if counts.pending:
        return "pending"
    return "completed"


def current_version(content: Content):
    for version in content.versions:
        if version.is_current:
            return version
    return None


def collect_setting_issues(setting: ProjectSetting) -> list[SettingCompletenessIssueDTO]:
    issues = build_primary_summary_issues(setting)
    issues.extend(build_optional_summary_issues(setting))
    return issues


def build_primary_summary_issues(setting: ProjectSetting) -> list[SettingCompletenessIssueDTO]:
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
        issues.append(issue("genre", "建议补一句题材/类型，方便快速识别项目方向"))
    if not has_protagonist_entry:
        issues.append(
            issue(
                "protagonist.identity",
                "建议补一句主角身份或初始处境，方便快速浏览人物入口",
            )
        )
    if not (protagonist and protagonist.goal):
        issues.append(issue("protagonist.goal", "建议补一句主角目标，便于后续摘要和检索"))
    if not setting.core_conflict:
        issues.append(issue("core_conflict", "建议补一句核心冲突，方便快速看出故事张力"))
    if not has_world_baseline:
        issues.append(
            issue(
                "world_setting",
                "建议补一句时代背景、世界规则、力量体系或关键地点，方便快速定位世界基线",
            )
        )
    return issues


def build_optional_summary_issues(setting: ProjectSetting) -> list[SettingCompletenessIssueDTO]:
    issues: list[SettingCompletenessIssueDTO] = []
    scale = setting.scale
    has_scale = bool(scale and (scale.target_words or scale.target_chapters))
    if not setting.tone:
        issues.append(issue("tone", "建议补一句基调/风格，方便统一整体气质"))
    if not has_scale:
        issues.append(issue("scale", "建议补一下目标篇幅或章节规模，方便预算和规划"))
    return issues


def resolve_status(issues: list[SettingCompletenessIssueDTO]) -> str:
    if issues:
        return "warning"
    return "ready"


def issue(
    field: str,
    message: str,
) -> SettingCompletenessIssueDTO:
    return SettingCompletenessIssueDTO(field=field, level="warning", message=message)
