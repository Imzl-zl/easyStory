"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
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
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {errorMessage}
      </div>
    );
  }

  if (isLoading && summary === null) {
    return (
      <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">
        正在汇总预算窗口、类型拆分和调用明细…
      </div>
    );
  }

  if (summary === null) {
    return (
      <EmptyState
        title="暂无账单摘要"
        description="先载入一个 workflow，账单面板才会显示预算窗口与 Token 使用详情。"
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <BillingMetricCard
          label="总 Token"
          value={formatTokenCount(summary.total_tokens)}
          detail={`${formatTokenCount(summary.total_input_tokens)} 输入 / ${formatTokenCount(summary.total_output_tokens)} 输出`}
        />
        <BillingMetricCard
          label="预估成本"
          value={formatUsdCost(summary.total_estimated_cost)}
          detail={`策略：${formatExceedStrategyLabel(summary.on_exceed)}`}
        />
        <BillingMetricCard
          label="预算参考点"
          value={formatDateTime(summary.budget_recorded_at)}
          detail="日级预算围绕这次最近 usage 归档"
        />
        <BillingMetricCard
          label="统计窗口"
          value={formatBudgetWindow(summary.budget_window_start_at, summary.budget_window_end_at)}
          detail="project_day / user_day 使用同一窗口"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-4">
          <section className="panel-muted space-y-3 p-4">
            <header className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">预算状态</h3>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
                先看哪一层接近上限，再决定是继续跑还是先收缩预算。
              </p>
            </header>
            <div className="space-y-3">
              {summary.budget_statuses.map((status) => (
                <div
                  key={status.scope}
                  className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-[var(--text-primary)]">
                        {formatBudgetScopeLabel(status.scope)}
                      </p>
                      <p className="text-sm text-[var(--text-secondary)]">
                        已用 {formatTokenCount(status.used_tokens)} / 上限 {formatTokenCount(status.limit_tokens)}
                      </p>
                    </div>
                    <StatusBadge
                      status={resolveBudgetTone(status)}
                      label={resolveBudgetLabel(status)}
                    />
                  </div>
                  <p className="mt-3 text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">
                    告警阈值 {formatWarningThreshold(status.warning_threshold)}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="panel-muted space-y-3 p-4">
            <header className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">用途拆分</h3>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
                判断成本主要花在生成、审核还是精修，而不是只看总量。
              </p>
            </header>
            {summary.usage_by_type.length > 0 ? (
              <div className="space-y-3">
                {summary.usage_by_type.map((usage) => (
                  <div
                    key={usage.usage_type}
                    className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {formatUsageTypeLabel(usage.usage_type)}
                        </p>
                        <p className="text-sm text-[var(--text-secondary)]">
                          {usage.call_count} 次调用，{formatTokenCount(usage.total_tokens)} tokens
                        </p>
                      </div>
                      <p className="text-sm font-medium text-[var(--accent-ink)]">
                        {formatUsdCost(usage.estimated_cost)}
                      </p>
                    </div>
                    <p className="mt-3 text-xs text-[var(--text-secondary)]">
                      输入 {formatTokenCount(usage.input_tokens)} / 输出 {formatTokenCount(usage.output_tokens)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">当前 workflow 还没有记录到 token usage。</p>
            )}
          </section>
        </div>

        <section className="panel-muted space-y-3 p-4">
          <header className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">调用明细</h3>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              按时间倒序查看每次模型调用，快速定位哪一步骤突然放大了成本。
            </p>
          </header>
          {usages.length > 0 ? (
            <div className="space-y-3">
              {usages.map((usage) => (
                <div
                  key={usage.id}
                  className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status="active" label={formatUsageTypeLabel(usage.usage_type)} />
                      <span className="text-sm font-medium text-[var(--text-primary)]">
                        {usage.model_name}
                      </span>
                    </div>
                    <span className="text-sm text-[var(--text-secondary)]">
                      {formatDateTime(usage.created_at)}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-4">
                    <UsageMetric label="输入" value={formatTokenCount(usage.input_tokens)} />
                    <UsageMetric label="输出" value={formatTokenCount(usage.output_tokens)} />
                    <UsageMetric label="总量" value={formatTokenCount(usage.total_tokens)} />
                    <UsageMetric label="成本" value={formatUsdCost(usage.estimated_cost)} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-secondary)]">当前 workflow 还没有落库的调用明细。</p>
          )}
        </section>
      </div>
    </div>
  );
}

function BillingMetricCard({
  label,
  value,
  detail,
}: Readonly<{
  label: string;
  value: string;
  detail: string;
}>) {
  return (
    <div className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">{label}</p>
      <p className="mt-3 font-serif text-xl leading-8 text-[var(--text-primary)]">{value}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{detail}</p>
    </div>
  );
}

function UsageMetric({
  label,
  value,
}: Readonly<{
  label: string;
  value: string;
}>) {
  return (
    <div className="rounded-2xl bg-[rgba(241,236,227,0.72)] px-3 py-3">
      <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-secondary)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
