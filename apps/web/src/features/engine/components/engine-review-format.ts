import type {
  WorkflowReviewAction,
  WorkflowReviewIssue,
  WorkflowReviewIssueCategory,
  WorkflowReviewIssueSeverity,
  WorkflowReviewStatus,
} from "@/lib/api/types";
import { formatEngineDateTime } from "./engine-datetime-format";

const NUMBER_FORMATTER = new Intl.NumberFormat("zh-CN");

const REVIEW_STATUS_LABELS: Record<WorkflowReviewStatus, string> = {
  passed: "通过",
  failed: "失败",
  warning: "警告",
};

const ISSUE_SEVERITY_LABELS: Record<WorkflowReviewIssueSeverity, string> = {
  critical: "严重",
  major: "主要",
  minor: "次要",
  suggestion: "建议",
};

const ISSUE_CATEGORY_LABELS: Record<WorkflowReviewIssueCategory, string> = {
  plot_inconsistency: "情节冲突",
  character_inconsistency: "角色不一致",
  style_deviation: "风格偏移",
  banned_words: "禁用词",
  ai_flavor: "AI 痕迹",
  logic_error: "逻辑错误",
  quality_low: "质量偏低",
  other: "其他",
};

export function formatCount(value: number): string {
  return NUMBER_FORMATTER.format(value);
}

export function formatDateTime(value: string | null): string {
  return formatEngineDateTime(value);
}

export function formatReviewStatusLabel(value: WorkflowReviewStatus): string {
  return REVIEW_STATUS_LABELS[value];
}

export function formatIssueSeverityLabel(value: WorkflowReviewIssueSeverity): string {
  return ISSUE_SEVERITY_LABELS[value];
}

export function formatIssueCategoryLabel(value: WorkflowReviewIssueCategory): string {
  return ISSUE_CATEGORY_LABELS[value];
}

export function formatReviewTypeLabel(value: string): string {
  return value
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatScore(value: number | null): string {
  if (value === null) {
    return "未评分";
  }
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)} 分`;
}

export function formatExecutionTime(value: number | null): string {
  if (value === null) {
    return "未记录";
  }
  if (value < 1000) {
    return `${NUMBER_FORMATTER.format(value)} ms`;
  }
  return `${(value / 1000).toFixed(value >= 10_000 ? 0 : 1)} s`;
}

export function formatTokensUsed(value: number | null): string {
  if (value === null) {
    return "未记录";
  }
  return `${NUMBER_FORMATTER.format(value)} tokens`;
}

export function formatReviewerLabel(action: WorkflowReviewAction): string {
  return action.reviewer_name ?? action.agent_id;
}

export function formatNodeLabel(action: WorkflowReviewAction): string {
  return `${action.node_type} · ${action.node_id} · #${action.node_order}`;
}

export function formatIssueLocation(issue: WorkflowReviewIssue): string | null {
  if (!issue.location) {
    return null;
  }

  const parts = [
    issue.location.paragraph_index === null ? null : `段落 ${issue.location.paragraph_index + 1}`,
    issue.location.start_offset === null ? null : `偏移 ${issue.location.start_offset}`,
    issue.location.end_offset === null ? null : `结束 ${issue.location.end_offset}`,
  ].filter(Boolean);

  return parts.length > 0 ? parts.join(" · ") : null;
}

export function resolveIssueTone(severity: WorkflowReviewIssueSeverity): "failed" | "warning" | "active" {
  if (severity === "critical" || severity === "major") {
    return "failed";
  }
  if (severity === "minor") {
    return "warning";
  }
  return "active";
}
