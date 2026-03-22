import type { AnalysisSummary, ContextPreviewSection } from "@/lib/api/types";

const NUMBER_FORMATTER = new Intl.NumberFormat("zh-CN");

const DATETIME_FORMATTER = new Intl.DateTimeFormat("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const SECTION_LABELS: Record<string, string> = {
  project_setting: "项目设定",
  outline: "大纲",
  opening_plan: "开篇设计",
  chapter_task: "章节任务",
  previous_chapters: "前文",
  story_bible: "Story Bible",
  style_reference: "风格参考",
};

const SECTION_STATUS_LABELS: Record<string, string> = {
  included: "已注入",
  degraded: "已降级",
  unused: "未引用",
  not_applicable: "当前不适用",
  dropped: "已裁剪",
  missing: "缺失",
};

export function formatCount(value: number): string {
  return NUMBER_FORMATTER.format(value);
}

export function formatTokenCount(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "-";
  }
  return `${NUMBER_FORMATTER.format(value)} tokens`;
}

export function formatSectionLabel(value: string): string {
  return SECTION_LABELS[value] ?? value;
}

export function formatSectionStatusLabel(value: string): string {
  return SECTION_STATUS_LABELS[value] ?? value;
}

export function formatAnalysisOptionLabel(analysis: AnalysisSummary): string {
  const sourceTitle = analysis.source_title ?? "未命名来源";
  const skillKey = analysis.generated_skill_key ?? "无 skill key";
  return `${sourceTitle} · ${skillKey} · ${formatDateTime(analysis.created_at)}`;
}

export function resolveSectionTone(status: string): "active" | "warning" | "draft" | "failed" | "stale" {
  if (status === "included") {
    return "active";
  }
  if (status === "degraded") {
    return "warning";
  }
  if (status === "missing") {
    return "failed";
  }
  if (status === "dropped") {
    return "stale";
  }
  return "draft";
}

export function buildSectionDetail(section: ContextPreviewSection): string[] {
  const lines = [`当前占用 ${formatTokenCount(section.token_count)}`];

  if (typeof section.original_tokens === "number" && section.original_tokens > section.token_count) {
    lines.push(`原始大小 ${formatTokenCount(section.original_tokens)}`);
  }
  if (section.selected_fields && section.selected_fields.length > 0) {
    lines.push(`字段 ${section.selected_fields.join(", ")}`);
  }
  if (typeof section.items_count === "number") {
    lines.push(`条目 ${formatCount(section.items_count)}`);
  }
  if (typeof section.items_truncated === "number" && section.items_truncated > 0) {
    lines.push(`裁掉 ${formatCount(section.items_truncated)} 条`);
  }
  if (section.phase) {
    lines.push(`阶段 ${section.phase}`);
  }

  return lines;
}

function formatDateTime(value: string): string {
  return `${DATETIME_FORMATTER.format(new Date(value))} UTC`;
}
