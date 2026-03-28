import type { QueryClient } from "@tanstack/react-query";

import type {
  ProjectSetting,
  ProjectSettingImpactSummary,
  SettingCompletenessResult,
} from "@/lib/api/types";

export const EMPTY_SETTING: ProjectSetting = {
  protagonist: {},
  world_setting: {},
  scale: {},
};

export function buildSettingSaveFeedback(impact: ProjectSettingImpactSummary) {
  if (!impact.has_impact) {
    return "项目设定已保存，当前没有需要重新标记的下游内容。";
  }
  return `项目设定已保存，并同步标记 ${impact.total_affected_entries} 个下游项为 stale。`;
}

export function buildSettingIssueSummary(completeness?: SettingCompletenessResult) {
  if (!completeness || completeness.issues.length === 0) {
    return "当前没有阻塞或警告项。";
  }
  return completeness.issues.map((issue) => `${issue.field}: ${issue.message}`).join(" / ");
}

export function isProjectSettingDirty(currentSetting: ProjectSetting, initialSetting: ProjectSetting): boolean {
  return JSON.stringify(currentSetting) !== JSON.stringify(initialSetting);
}

export function invalidateProjectSettingQueries(
  queryClient: QueryClient,
  projectId: string,
  impact: ProjectSettingImpactSummary,
) {
  queryClient.invalidateQueries({ queryKey: ["project", projectId] });
  queryClient.invalidateQueries({ queryKey: ["setting-check", projectId] });
  queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
  if (impact.items.some((item) => item.target === "outline")) {
    queryClient.invalidateQueries({ queryKey: ["story-asset", projectId, "outline"] });
  }
  if (impact.items.some((item) => item.target === "opening_plan")) {
    queryClient.invalidateQueries({ queryKey: ["story-asset", projectId, "opening_plan"] });
  }
  if (impact.items.some((item) => item.target === "chapter")) {
    queryClient.invalidateQueries({ queryKey: ["chapters", projectId] });
  }
}
