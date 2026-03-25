import type { ChapterTaskView } from "@/lib/api/types";

const EXPORT_FORMAT_SEQUENCE = ["txt", "markdown"] as const;

export const DEFAULT_EXPORT_FORMATS = [...EXPORT_FORMAT_SEQUENCE];

type ExportPrecheckLevel = "blocking" | "warning" | "info";

export type ExportPrecheckItem = {
  chapterNumber: number;
  detail: string;
  level: ExportPrecheckLevel;
  title: string;
};

export type ExportPrecheck = {
  blockingItems: ExportPrecheckItem[];
  infoItems: ExportPrecheckItem[];
  warningItems: ExportPrecheckItem[];
};

const EXPORT_FORMAT_ORDER = new Map<string, number>(
  EXPORT_FORMAT_SEQUENCE.map((value, index) => [value, index]),
);

export function buildExportPrecheck(tasks: ChapterTaskView[]): ExportPrecheck {
  const precheck: ExportPrecheck = {
    blockingItems: [],
    infoItems: [],
    warningItems: [],
  };

  tasks.forEach((task) => {
    if (task.status === "skipped") {
      precheck.infoItems.push({
        chapterNumber: task.chapter_number,
        detail: "该章节被显式跳过，本次导出会直接省略，不会生成占位内容。",
        level: "info",
        title: "章节已跳过",
      });
      return;
    }
    if (task.status === "completed" || task.status === "stale") {
      if (!task.content_id) {
        precheck.blockingItems.push(
          toPrecheckItem(
            task.chapter_number,
            "缺少已确认正文",
            "当前章节没有绑定可导出的已确认正文，需先补齐正文真值后再导出。",
          ),
        );
        return;
      }
    }
    if (task.status === "completed") {
      return;
    }
    if (task.status === "stale") {
      precheck.warningItems.push({
        chapterNumber: task.chapter_number,
        detail: "当前正文可能基于旧上下文，允许导出，但应优先回到章节任务面板重建计划。",
        level: "warning",
        title: "章节已失效",
      });
      return;
    }
    precheck.blockingItems.push(buildBlockingItem(task));
  });

  return precheck;
}

export function formatExportFileSize(size: number | null): string {
  if (size === null || size <= 0) {
    return "体积未知";
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatExportTimestamp(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function resolveExportCreateDisabledReason({
  blockingCount,
  hasWorkflow,
  selectedFormatsCount,
  taskCount,
}: {
  blockingCount: number;
  hasWorkflow: boolean;
  selectedFormatsCount: number;
  taskCount: number;
}): string | null {
  if (!hasWorkflow) {
    return "请先载入一个 workflow，再从该工作流发起导出。";
  }
  if (taskCount === 0) {
    return "当前 workflow 还没有章节任务真值，无法导出。";
  }
  if (selectedFormatsCount === 0) {
    return "至少选择一种导出格式。";
  }
  if (blockingCount > 0) {
    return "当前存在未完成章节，需先处理阻断项后再导出。";
  }
  return null;
}

export function toggleExportFormat(current: string[], next: string): string[] {
  const values = new Set(current);
  if (values.has(next)) {
    values.delete(next);
  } else {
    values.add(next);
  }
  return Array.from(values).sort(compareExportFormat);
}

function buildBlockingItem(task: ChapterTaskView): ExportPrecheckItem {
  if (task.status === "pending") {
    return toPrecheckItem(task.chapter_number, "章节未开始", "当前章节尚未开始执行，导出会缺失正文。");
  }
  if (task.status === "generating" && task.content_id) {
    return toPrecheckItem(task.chapter_number, "章节待确认", "当前章节已有草稿，但尚未确认成当前正文，暂不可导出。");
  }
  if (task.status === "generating") {
    return toPrecheckItem(task.chapter_number, "章节生成中", "当前章节仍在生成中，请等待任务完成后再导出。");
  }
  if (task.status === "interrupted") {
    return toPrecheckItem(task.chapter_number, "章节已中断", "当前章节任务已被打断，需要先恢复或修正。");
  }
  if (task.status === "failed") {
    return toPrecheckItem(task.chapter_number, "章节生成失败", "当前章节没有可用成稿，需先处理失败原因。");
  }
  return toPrecheckItem(task.chapter_number, "章节状态异常", `当前章节状态为 ${task.status}，暂不可导出。`);
}

function compareExportFormat(left: string, right: string): number {
  return (EXPORT_FORMAT_ORDER.get(left) ?? Number.MAX_SAFE_INTEGER) - (EXPORT_FORMAT_ORDER.get(right) ?? Number.MAX_SAFE_INTEGER);
}

function toPrecheckItem(
  chapterNumber: number,
  title: string,
  detail: string,
): ExportPrecheckItem {
  return {
    chapterNumber,
    detail,
    level: "blocking",
    title,
  };
}
