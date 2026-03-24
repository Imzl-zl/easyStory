import type { QueryClient } from "@tanstack/react-query";

import type { StoryAssetImpactSummary } from "@/lib/api/types";

type StoryAssetType = "outline" | "opening_plan";
type StoryAssetAction = "save" | "approve";

const STORY_ASSET_LABELS = {
  outline: "大纲",
  opening_plan: "开篇设计",
} as const;

export function getStoryAssetLabel(assetType: StoryAssetType) {
  return STORY_ASSET_LABELS[assetType];
}

export function buildStoryAssetMutationFeedback(
  assetType: StoryAssetType,
  action: StoryAssetAction,
  impact: StoryAssetImpactSummary,
) {
  const verb = action === "save" ? "已保存" : "已确认";
  const label = getStoryAssetLabel(assetType);
  if (!impact.has_impact) {
    return `${label}${verb}，当前没有新的下游 stale 影响。`;
  }
  return `${label}${verb}，并同步标记 ${impact.total_affected_entries} 个下游项为 stale。`;
}

export function invalidateStoryAssetQueries(
  queryClient: QueryClient,
  projectId: string,
  assetType: StoryAssetType,
  impact: StoryAssetImpactSummary,
) {
  queryClient.invalidateQueries({ queryKey: ["story-asset", projectId, assetType] });
  queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
  if (impact.items.some((item) => item.target === "opening_plan")) {
    queryClient.invalidateQueries({ queryKey: ["story-asset", projectId, "opening_plan"] });
  }
  if (impact.items.some((item) => item.target === "chapter")) {
    queryClient.invalidateQueries({ queryKey: ["chapters", projectId] });
  }
}
