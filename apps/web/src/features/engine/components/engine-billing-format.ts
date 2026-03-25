import type {
  TokenUsageView,
  WorkflowBillingBudgetStatus,
  WorkflowBillingUsageBreakdown,
} from "@/lib/api/types";
import { formatEngineDateTime } from "./engine-datetime-format";

const NUMBER_FORMATTER = new Intl.NumberFormat("zh-CN");

const PERCENT_FORMATTER = new Intl.NumberFormat("zh-CN", {
  style: "percent",
  maximumFractionDigits: 0,
});

const USAGE_TYPE_LABELS: Record<TokenUsageView["usage_type"], string> = {
  generate: "生成",
  review: "审核",
  fix: "精修",
  analysis: "分析",
  dry_run: "预估",
};

const SCOPE_LABELS: Record<WorkflowBillingBudgetStatus["scope"], string> = {
  workflow: "本次工作流",
  project_day: "项目日预算",
  user_day: "用户日预算",
};

const EXCEED_STRATEGY_LABELS = {
  pause: "超限后暂停",
  skip: "超限后跳过",
  fail: "超限后失败",
} as const;

export function formatTokenCount(value: number): string {
  return NUMBER_FORMATTER.format(value);
}

export function formatUsdCost(value: string): string {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return `$${value}`;
  }
  return `$${amount.toFixed(amount >= 0.1 ? 2 : 4)}`;
}

export function formatDateTime(value: string): string {
  return formatEngineDateTime(value);
}

export function formatBudgetWindow(startAt: string, endAt: string): string {
  return `${formatDateTime(startAt)} - ${formatDateTime(endAt)}`;
}

export function formatUsageTypeLabel(value: WorkflowBillingUsageBreakdown["usage_type"]): string {
  return USAGE_TYPE_LABELS[value];
}

export function formatBudgetScopeLabel(value: WorkflowBillingBudgetStatus["scope"]): string {
  return SCOPE_LABELS[value];
}

export function formatExceedStrategyLabel(value: "pause" | "skip" | "fail"): string {
  return EXCEED_STRATEGY_LABELS[value];
}

export function formatWarningThreshold(value: number): string {
  return PERCENT_FORMATTER.format(value);
}

export function resolveBudgetTone(status: WorkflowBillingBudgetStatus): "active" | "stale" | "failed" {
  if (status.exceeded) {
    return "failed";
  }
  if (status.warning_reached) {
    return "stale";
  }
  return "active";
}

export function resolveBudgetLabel(status: WorkflowBillingBudgetStatus): string {
  if (status.exceeded) {
    return "已超限";
  }
  if (status.warning_reached) {
    return "已告警";
  }
  return "正常";
}
