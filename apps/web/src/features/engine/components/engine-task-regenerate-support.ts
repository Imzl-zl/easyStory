import type { ChapterTaskDraft, ChapterTaskView } from "@/lib/api/types";

export const REGENERATE_CONFIRMATION_MESSAGE =
  "重建将覆盖当前章节计划，已生成的草稿将被标记为失效。";

export function buildRegenerateConfirmationItems(
  currentTasks: ChapterTaskView[],
  nextTasks: ChapterTaskDraft[],
): string[] {
  const items = [`即将提交 ${nextTasks.length} 条章节任务草稿。`];
  const chapterRange = formatChapterRange(nextTasks);

  if (chapterRange) {
    items.push(chapterRange);
  }
  if (currentTasks.length === 0) {
    items.push("当前 workflow 还没有章节任务真值，本次会直接建立新的章节计划。");
    return items;
  }

  items.push(`现有 ${currentTasks.length} 条章节任务会被整体覆盖。`);
  const staleTaskCount = countTasksByStatus(currentTasks, "stale");
  if (staleTaskCount > 0) {
    items.push(`其中 ${staleTaskCount} 条已失效任务会被新计划替换。`);
  }
  return items;
}

function countTasksByStatus(
  tasks: ChapterTaskView[],
  status: ChapterTaskView["status"],
): number {
  return tasks.filter((task) => task.status === status).length;
}

function formatChapterRange(tasks: ChapterTaskDraft[]): string | null {
  const first = tasks[0]?.chapter_number;
  const last = tasks[tasks.length - 1]?.chapter_number;

  if (first === undefined || last === undefined) {
    return null;
  }
  if (first === last) {
    return `本次重建范围为第 ${first} 章。`;
  }
  return `本次重建范围为第 ${first} 至第 ${last} 章。`;
}
