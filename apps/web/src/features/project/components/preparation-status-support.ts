import type {
  PreparationAssetStatus,
  PreparationChapterTaskStatus,
  PreparationNextStep,
  ProjectPreparationStatus,
} from "@/lib/api/types";

export type PreparationStatusRow = {
  description: string;
  label: string;
  status: string;
};

const NEXT_STEP_LABELS: Record<PreparationNextStep, string> = {
  setting: "项目设定",
  outline: "大纲",
  opening_plan: "开篇设计",
  chapter_tasks: "章节任务",
  workflow: "工作流",
  chapter: "正文",
};

const STATUS_LABELS: Record<string, string> = {
  ready: "就绪",
  warning: "警告",
  not_started: "未开始",
  draft: "草稿",
  approved: "已确认",
  stale: "已失效",
  archived: "已归档",
  pending: "未开始",
  generating: "进行中",
  completed: "已确认",
  failed: "失败",
  interrupted: "已中断",
  setting: "待设定",
  outline: "待大纲",
  opening_plan: "待开篇",
  chapter_tasks: "待任务",
  workflow: "待工作流",
  chapter: "待正文",
};

export function buildPreparationStatusRows(
  preparation: ProjectPreparationStatus,
): PreparationStatusRow[] {
  return [
    {
      label: "结构化摘要",
      status: preparation.setting.status,
      description: describeSettingStatus(preparation.setting),
    },
    {
      label: "大纲",
      status: preparation.outline.step_status,
      description: describeAssetStatus(preparation.outline, "先明确故事主骨架"),
    },
    {
      label: "开篇设计",
      status: preparation.opening_plan.step_status,
      description: describeAssetStatus(preparation.opening_plan, "前 1-3 章的阶段约束"),
    },
    {
      label: "章节任务",
      status: preparation.chapter_tasks.step_status,
      description: describeTaskStatus(preparation.chapter_tasks),
    },
  ];
}

export function formatPreparationNextStep(step: PreparationNextStep): string {
  return NEXT_STEP_LABELS[step] ?? step;
}

export function formatPreparationStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function describeSettingStatus(setting: ProjectPreparationStatus["setting"]): string {
  if (setting.issues.length === 0) {
    return "结构化摘要已覆盖主要信息，后续可继续在项目文档里维护详细设定。";
  }
  return setting.issues.map((issue) => issue.message).join(" / ");
}

export function describeAssetStatus(
  asset: PreparationAssetStatus,
  fallback: string,
): string {
  switch (asset.step_status) {
    case "not_started":
      return fallback;
    case "draft":
      return `当前为草稿，第 ${asset.version_number ?? "?"} 版，尚未确认。`;
    case "approved":
      return `当前为已确认版本，第 ${asset.version_number ?? "?"} 版。`;
    case "stale":
      return "上游真值已变化，当前内容已失效，需要重新检查或生成。";
    case "archived":
      return "当前内容已归档。";
  }
}

export function describeTaskStatus(chapterTasks: PreparationChapterTaskStatus): string {
  if (chapterTasks.step_status === "not_started") {
    return "尚未生成章节任务。";
  }

  const parts = [`共 ${chapterTasks.total} 个任务`];
  appendTaskCount(parts, chapterTasks.counts.pending, "未开始");
  appendTaskCount(parts, chapterTasks.counts.generating, "进行中");
  appendTaskCount(parts, chapterTasks.counts.completed, "已确认");
  appendTaskCount(parts, chapterTasks.counts.stale, "已失效");
  appendTaskCount(parts, chapterTasks.counts.failed, "失败");
  appendTaskCount(parts, chapterTasks.counts.interrupted, "已中断");
  appendTaskCount(parts, chapterTasks.counts.skipped, "已跳过");
  return parts.join(" / ");
}

function appendTaskCount(parts: string[], count: number, label: string) {
  if (count > 0) {
    parts.push(`${count} 个${label}`);
  }
}
