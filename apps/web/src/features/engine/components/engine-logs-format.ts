import type { ExecutionLogLevel, NodeExecutionStatus } from "@/lib/api/types";

const DATETIME_FORMATTER = new Intl.DateTimeFormat("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const NUMBER_FORMATTER = new Intl.NumberFormat("zh-CN");

const EXECUTION_STATUS_LABELS: Record<NodeExecutionStatus, string> = {
  pending: "等待中",
  running: "执行中",
  completed: "已完成",
  skipped: "已跳过",
  failed: "失败",
  running_stream: "流式执行",
  reviewing: "审核中",
  fixing: "精修中",
  interrupted: "已中断",
};

const LOG_LEVEL_LABELS: Record<ExecutionLogLevel, string> = {
  INFO: "信息",
  WARNING: "警告",
  ERROR: "错误",
};

export function formatCount(value: number): string {
  return NUMBER_FORMATTER.format(value);
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "暂无";
  }
  return `${DATETIME_FORMATTER.format(new Date(value))} UTC`;
}

export function formatExecutionStatusLabel(value: NodeExecutionStatus): string {
  return EXECUTION_STATUS_LABELS[value];
}

export function formatLogLevelLabel(value: ExecutionLogLevel): string {
  return LOG_LEVEL_LABELS[value];
}

export function formatDuration(value: number | null): string {
  if (value === null) {
    return "未记录";
  }
  if (value < 1000) {
    return `${NUMBER_FORMATTER.format(value)} ms`;
  }
  return `${(value / 1000).toFixed(value >= 10_000 ? 0 : 1)} s`;
}

export function formatShortId(value: string | null): string {
  if (!value) {
    return "无";
  }
  return value.slice(0, 8);
}

export function resolveExecutionTone(status: NodeExecutionStatus): "draft" | "active" | "completed" | "warning" | "failed" | "stale" {
  if (status === "completed") {
    return "completed";
  }
  if (status === "failed") {
    return "failed";
  }
  if (status === "skipped") {
    return "stale";
  }
  if (status === "interrupted") {
    return "warning";
  }
  if (status === "pending") {
    return "draft";
  }
  return "active";
}

export function resolveLogLevelTone(level: ExecutionLogLevel): "active" | "warning" | "failed" {
  if (level === "ERROR") {
    return "failed";
  }
  if (level === "WARNING") {
    return "warning";
  }
  return "active";
}
