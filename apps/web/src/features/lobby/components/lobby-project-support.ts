import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import type { AppNoticeTone } from "@/components/ui/app-notice";
import type { ProjectSummary, ProjectTrashCleanupResult } from "@/lib/api/types";

const DAY_IN_MS = 24 * 60 * 60 * 1000;

export const PROJECT_TRASH_RETENTION_DAYS = 30;

export type ProjectActionType = "delete" | "restore" | "physicalDelete";

type ProjectNotice = {
  content: string;
  title: string;
  tone: AppNoticeTone;
};

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

export function resolveProjectActionNotice(type: ProjectActionType): ProjectNotice {
  return {
    content: resolveProjectActionMessage(type),
    title: "项目",
    tone: "success",
  };
}

export function resolveEmptyTrashButtonLabel(isPending: boolean): string {
  return isPending ? "清空中..." : "清空回收站";
}

export function resolveEmptyTrashNotice(result: ProjectTrashCleanupResult): ProjectNotice {
  return {
    content: buildEmptyTrashFeedback(result),
    title: "回收站",
    tone: resolveEmptyTrashNoticeTone(result),
  };
}

function buildEmptyTrashFeedback(result: ProjectTrashCleanupResult): string {
  if (
    result.deleted_count === 0 &&
    result.skipped_count === 0 &&
    result.failed_count === 0
  ) {
    return "回收站已经是空的。";
  }
  if (result.failed_count === 0 && result.skipped_count === 0) {
    return `已清空回收站，共彻底删除 ${result.deleted_count} 个项目。`;
  }
  const segments: string[] = [];
  if (result.deleted_count > 0) {
    segments.push(`已彻底删除 ${result.deleted_count} 个项目`);
  }
  if (result.skipped_count > 0) {
    segments.push(`跳过 ${result.skipped_count} 个已恢复项目`);
  }
  if (result.failed_count > 0) {
    segments.push(`另有 ${result.failed_count} 个项目清理异常`);
  }
  const summary = `${segments.join("，")}。`;
  if (result.failed_count === 0) {
    return summary;
  }
  return `${summary}请稍后重试或查看后端日志。`;
}

function resolveProjectActionMessage(type: ProjectActionType): string {
  if (type === "delete") {
    return "项目已移入回收站。";
  }
  if (type === "restore") {
    return "项目已恢复。";
  }
  return "项目已彻底删除。";
}

function resolveEmptyTrashNoticeTone(result: ProjectTrashCleanupResult): AppNoticeTone {
  if (result.failed_count > 0) {
    return "warning";
  }
  if (result.deleted_count > 0) {
    return "success";
  }
  return "info";
}
