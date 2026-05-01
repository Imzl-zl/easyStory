"use client";

import { EmptyState } from "@/components/ui/empty-state";
import type { TokenUsageView, WorkflowBillingSummary } from "@/lib/api/types";

import {
  formatBudgetScopeLabel,
  formatBudgetWindow,
  formatDateTime,
  formatExceedStrategyLabel,
  formatTokenCount,
  formatUsageTypeLabel,
  formatUsdCost,
  formatWarningThreshold,
  resolveBudgetLabel,
  resolveBudgetTone,
} from "./engine-billing-format";

type EngineBillingPanelProps = {
  summary: WorkflowBillingSummary | null;
  usages: TokenUsageView[];
  isLoading: boolean;
  errorMessage: string | null;
};

export function EngineBillingPanel({
  summary,
  usages,
  isLoading,
  errorMessage,
}: EngineBillingPanelProps) {
  if (errorMessage) {
    return (
      <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
        {errorMessage}
      </div>
    );
  }

  if (isLoading && summary === null) {
    return (
      <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}>
        正在汇总预算窗口、类型拆分和调用明细…
      </div>
    );
  }

  if (summary === null) {
    return (
      <EmptyState
        title="暂无账单摘要"
        description="载入工作流后查看。"
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2 grid-cols-2 md:grid-cols-4">
        <MetricItem label="总 Token" value={formatTokenCount(summary.total_tokens)} detail={`${formatTokenCount(summary.total_input_tokens)} 输入 / ${formatTokenCount(summary.total_output_tokens)} 输出`} />
        <MetricItem label="预估成本" value={formatUsdCost(summary.total_estimated_cost)} detail={`策略：${formatExceedStrategyLabel(summary.on_exceed)}`} />
        <MetricItem label="预算参考点" value={formatDateTime(summary.budget_recorded_at)} detail="日级预算围绕这次最近 usage 归档" />
        <MetricItem label="统计窗口" value={formatBudgetWindow(summary.budget_window_start_at, summary.budget_window_end_at)} detail="project_day / user_day 使用同一窗口" />
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-3">
          <section className="space-y-2">
            <h3 className="text-[12px] font-medium" style={{ color: "var(--text-tertiary)" }}>预算状态</h3>
            <div className="space-y-2">
              {summary.budget_statuses.map((status) => (
                <div
                  key={status.scope}
                  className="rounded p-3"
                  style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="space-y-0.5">
                      <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
                        {formatBudgetScopeLabel(status.scope)}
                      </p>
                      <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                        已用 {formatTokenCount(status.used_tokens)} / 上限 {formatTokenCount(status.limit_tokens)}
                      </p>
                    </div>
                    <StatusPill tone={resolveBudgetTone(status)} label={resolveBudgetLabel(status)} />
                  </div>
                  <p className="mt-2 text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                    告警阈值 {formatWarningThreshold(status.warning_threshold)}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-2">
            <h3 className="text-[12px] font-medium" style={{ color: "var(--text-tertiary)" }}>用途拆分</h3>
            {summary.usage_by_type.length > 0 ? (
              <div className="space-y-2">
                {summary.usage_by_type.map((usage) => (
                  <div
                    key={usage.usage_type}
                    className="rounded p-3"
                    style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
                          {formatUsageTypeLabel(usage.usage_type)}
                        </p>
                        <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                          {usage.call_count} 次调用，{formatTokenCount(usage.total_tokens)} tokens
                        </p>
                      </div>
                      <p className="text-[12px] font-medium" style={{ color: "var(--accent-primary)" }}>
                        {formatUsdCost(usage.estimated_cost)}
                      </p>
                    </div>
                    <p className="mt-2 text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                      输入 {formatTokenCount(usage.input_tokens)} / 输出 {formatTokenCount(usage.output_tokens)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>暂无用量记录。</p>
            )}
          </section>
        </div>

        <section className="space-y-2">
          <h3 className="text-[12px] font-medium" style={{ color: "var(--text-tertiary)" }}>调用明细</h3>
          {usages.length > 0 ? (
            <div className="space-y-2">
              {usages.map((usage) => (
                <div
                  key={usage.id}
                  className="rounded p-3"
                  style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-1.5">
                      <StatusPill tone="active" label={formatUsageTypeLabel(usage.usage_type)} />
                      <span className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
                        {usage.model_name}
                      </span>
                    </div>
                    <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                      {formatDateTime(usage.created_at)}
                    </span>
                  </div>
                  <div className="mt-2 grid gap-2 grid-cols-4">
                    <MiniMetric label="输入" value={formatTokenCount(usage.input_tokens)} />
                    <MiniMetric label="输出" value={formatTokenCount(usage.output_tokens)} />
                    <MiniMetric label="总量" value={formatTokenCount(usage.total_tokens)} />
                    <MiniMetric label="成本" value={formatUsdCost(usage.estimated_cost)} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>暂无调用记录。</p>
          )}
        </section>
      </div>
    </div>
  );
}

function MetricItem({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded p-3" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
      <p className="text-[10px] mb-1" style={{ color: "var(--text-tertiary)" }}>{label}</p>
      <p className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>{value}</p>
      {detail ? <p className="text-[10px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>{detail}</p> : null}
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded p-2" style={{ background: "var(--bg-muted)" }}>
      <p className="text-[9px] mb-0.5" style={{ color: "var(--text-tertiary)" }}>{label}</p>
      <p className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>{value}</p>
    </div>
  );
}

function StatusPill({ tone, label }: { tone: string; label: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "var(--accent-success-soft)", text: "var(--accent-success)" },
    failed: { bg: "var(--accent-danger-soft)", text: "var(--accent-danger)" },
    warning: { bg: "var(--accent-warning-soft)", text: "var(--accent-warning)" },
    active: { bg: "var(--accent-primary-soft)", text: "var(--accent-primary)" },
    outline: { bg: "var(--line-soft)", text: "var(--text-secondary)" },
    draft: { bg: "var(--line-soft)", text: "var(--text-tertiary)" },
    success: { bg: "var(--accent-success-soft)", text: "var(--accent-success)" },
    danger: { bg: "var(--accent-danger-soft)", text: "var(--accent-danger)" },
  };
  const c = colors[tone] || colors.outline;
  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-medium"
      style={{ background: c.bg, color: c.text }}
    >
      {label}
    </span>
  );
}
