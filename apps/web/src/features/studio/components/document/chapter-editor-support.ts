import type { QueryClient } from "@tanstack/react-query";

import type { ChapterImpactSummary } from "@/lib/api/types";

type ChapterMutationAction = "save" | "rollback";

export function buildChapterMutationFeedback(
  action: ChapterMutationAction,
  impact: ChapterImpactSummary,
) {
  const verb = action === "save" ? "章节草稿已保存" : "已回滚到指定版本";
  if (!impact.has_impact) {
    return `${verb}，当前没有新的下游 stale 影响。`;
  }
  return `${verb}，并同步标记 ${impact.total_affected_entries} 个后续章节为 stale。`;
}

export function invalidateChapterQueries(
  queryClient: QueryClient,
  projectId: string,
  chapterNumber: number,
) {
  queryClient.invalidateQueries({ queryKey: ["chapters", projectId] });
  queryClient.invalidateQueries({ queryKey: ["chapter-detail", projectId, chapterNumber] });
  queryClient.invalidateQueries({ queryKey: ["chapter-versions", projectId, chapterNumber] });
}
