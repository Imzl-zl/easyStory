from __future__ import annotations

from collections import Counter

from app.modules.content.models import Content

from .dto import (
    AssetType,
    StoryAssetDTO,
    StoryAssetImpactItemDTO,
    StoryAssetImpactSummaryDTO,
    StoryAssetMutationDTO,
)

STALE_FROM_OUTLINE = frozenset({"opening_plan", "chapter"})
STALE_FROM_OPENING_PLAN = frozenset({"chapter"})
STALE_TRIGGER_ASSET_TYPES = frozenset({"outline", "opening_plan"})
STORY_ASSET_IMPACT_ORDER = ("opening_plan", "chapter")


def build_story_asset_mutation(
    asset: StoryAssetDTO,
    impact: StoryAssetImpactSummaryDTO | None = None,
) -> StoryAssetMutationDTO:
    return StoryAssetMutationDTO(
        **asset.model_dump(),
        impact=impact or StoryAssetImpactSummaryDTO(),
    )


def mark_downstream_stale(
    contents: list[Content],
    asset_type: AssetType,
) -> list[StoryAssetImpactItemDTO]:
    impacted_contents: list[Content] = []
    for content in contents:
        if content.status != "approved":
            continue
        if should_mark_downstream_stale(content, asset_type):
            content.status = "stale"
            impacted_contents.append(content)
    return build_story_asset_content_impacts(asset_type, impacted_contents)


def build_story_asset_content_impacts(
    asset_type: AssetType,
    contents: list[Content],
) -> list[StoryAssetImpactItemDTO]:
    counts = Counter(content.content_type for content in contents)
    impacts: list[StoryAssetImpactItemDTO] = []
    for target in STORY_ASSET_IMPACT_ORDER:
        count = counts.get(target, 0)
        if count:
            impacts.append(build_story_asset_impact_item(asset_type, target, count))
    return impacts


def build_story_asset_impact_summary(
    asset_type: AssetType,
    content_impacts: list[StoryAssetImpactItemDTO],
    *,
    stale_chapter_task_count: int,
) -> StoryAssetImpactSummaryDTO:
    items = list(content_impacts)
    if stale_chapter_task_count:
        items.append(
            build_story_asset_impact_item(
                asset_type,
                "chapter_tasks",
                stale_chapter_task_count,
            )
        )
    return StoryAssetImpactSummaryDTO(
        has_impact=bool(items),
        total_affected_entries=sum(item.count for item in items),
        items=items,
    )


def build_story_asset_impact_item(
    asset_type: AssetType,
    target: str,
    count: int,
) -> StoryAssetImpactItemDTO:
    return StoryAssetImpactItemDTO(
        target=target,
        action="mark_stale",
        count=count,
        message=format_story_asset_impact_message(asset_type, target, count),
    )


def format_story_asset_impact_message(
    asset_type: AssetType,
    target: str,
    count: int,
) -> str:
    if target == "opening_plan":
        return "已确认开篇设计将标记为 stale，需要在大纲稳定后重新确认"
    if target == "chapter":
        if asset_type == "outline":
            return f"{count} 个已确认章节将标记为 stale，需要基于最新大纲复核正文"
        return f"{count} 个前 1-3 章已确认正文将标记为 stale，需要根据最新开篇设计复核"
    if asset_type == "outline":
        return f"{count} 个章节任务将标记为 stale，需要重新执行 chapter_split"
    return f"{count} 个章节任务将标记为 stale，需要根据最新开篇设计重新拆分"


def should_mark_downstream_stale(
    content: Content,
    asset_type: AssetType,
) -> bool:
    if asset_type == "outline":
        return content.content_type in STALE_FROM_OUTLINE
    if content.content_type not in STALE_FROM_OPENING_PLAN:
        return False
    if content.chapter_number is None:
        return False
    return content.chapter_number <= 3
