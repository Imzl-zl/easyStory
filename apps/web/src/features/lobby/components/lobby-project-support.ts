import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import type { ProjectSummary } from "@/lib/api/types";

const DAY_IN_MS = 24 * 60 * 60 * 1000;

export const PROJECT_TRASH_RETENTION_DAYS = 30;

export type ProjectActionType = "delete" | "restore" | "physicalDelete";

export function buildFilteredProjects(
  projects: ProjectSummary[] | undefined,
  keyword: string,
): ProjectSummary[] {
  const normalizedKeyword = keyword.trim().toLowerCase();
  if (!normalizedKeyword) {
    return projects ?? [];
  }
  return (projects ?? []).filter((project) => project.name.toLowerCase().includes(normalizedKeyword));
}

export function formatProjectTargetWords(value: number | null): string {
  if (value === null) {
    return "未设定";
  }
  return `${new Intl.NumberFormat("zh-CN").format(value)} 字`;
}

export function formatProjectTrashTime(value: string | null): string {
  return formatObservabilityDateTime(value);
}

export function formatProjectTrashDeadline(
  value: string | null,
  retentionDays: number = PROJECT_TRASH_RETENTION_DAYS,
): string {
  if (!value) {
    return "暂无";
  }
  const expiresAt = new Date(new Date(value).getTime() + retentionDays * DAY_IN_MS);
  return formatObservabilityDateTime(expiresAt.toISOString());
}

export function resolveProjectActionButtonLabel(
  type: ProjectActionType,
  isPending: boolean,
): string {
  if (type === "delete") {
    return isPending ? "移入中..." : "移入回收站";
  }
  if (type === "restore") {
    return isPending ? "恢复中..." : "恢复项目";
  }
  return isPending ? "删除中..." : "彻底删除";
}

export function resolveProjectActionSuccessMessage(type: ProjectActionType): string {
  if (type === "delete") {
    return "项目已移入回收站。";
  }
  if (type === "restore") {
    return "项目已恢复。";
  }
  return "项目已彻底删除。";
}

export function resolveEmptyTrashButtonLabel(isPending: boolean): string {
  return isPending ? "清空中..." : "清空回收站";
}

export function resolveEmptyTrashFeedback(deletedCount: number): string {
  if (deletedCount === 0) {
    return "回收站已经是空的。";
  }
  return `已清空回收站，共彻底删除 ${deletedCount} 个项目。`;
}
