"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import type { WorkflowReviewAction, WorkflowReviewIssue, WorkflowReviewSummary } from "@/lib/api/types";

import {
  formatCount,
  formatDateTime,
  formatExecutionTime,
  formatIssueCategoryLabel,
  formatIssueLocation,
  formatIssueSeverityLabel,
  formatNodeLabel,
  formatReviewerLabel,
  formatReviewStatusLabel,
  formatReviewTypeLabel,
  formatScore,
  formatTokensUsed,
  resolveIssueTone,
} from "./engine-review-format";

type EngineReviewPanelProps = {
  summary: WorkflowReviewSummary | null;
  actions: WorkflowReviewAction[];
  isLoading: boolean;
  errorMessage: string | null;
};

export function EngineReviewPanel({ summary, actions, isLoading, errorMessage }: EngineReviewPanelProps) {
  if (errorMessage) {
    return <FeedbackMessage tone="danger" message={errorMessage} />;
  }

  if (isLoading && summary === null) {
    return <FeedbackMessage tone="muted" message="正在整理审核摘要、问题分级和 reviewer 动作…" />;
  }

  if (summary === null) {
    return (
      <EmptyState
        title="暂无审核摘要"
        description="载入工作流后，可以查看审核结果和问题分级。"
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <ReviewMetricCard
          label="审核节点"
          value={formatCount(summary.reviewed_node_count)}
          detail={`覆盖 ${formatCount(summary.total_actions)} 次审核动作`}
        />
        <ReviewMetricCard
          label="问题总数"
          value={formatCount(summary.issues.total)}
          detail={`严重/主要 ${formatCount(summary.issues.critical + summary.issues.major)}，次要/建议 ${formatCount(summary.issues.minor + summary.issues.suggestion)}`}
        />
        <ReviewMetricCard
          label="通过情况"
          value={`${formatCount(summary.statuses.passed)} / ${formatCount(summary.total_actions)}`}
          detail={`警告 ${formatCount(summary.statuses.warning)}，失败 ${formatCount(summary.statuses.failed)}`}
        />
        <ReviewMetricCard
          label="最近审核"
          value={formatDateTime(summary.last_reviewed_at)}
          detail={`工作流状态：${summary.workflow_status}`}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-4">
          <ReviewSummarySection summary={summary} />
          <ReviewTypesSection summary={summary} />
        </div>
        <ReviewActionsSection actions={actions} />
      </div>
    </div>
  );
}

function ReviewSummarySection({ summary }: Readonly<{ summary: WorkflowReviewSummary }>) {
  return (
    <section className="panel-muted space-y-3 p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">审核总览</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          先看通过/警告/失败分布，再判断问题是否集中在少数 reviewer 或节点。
        </p>
      </header>
      <div className="flex flex-wrap gap-2">
        <StatusBadge status="passed" label={`通过 ${formatCount(summary.statuses.passed)}`} />
        <StatusBadge status="warning" label={`警告 ${formatCount(summary.statuses.warning)}`} />
        <StatusBadge status="failed" label={`失败 ${formatCount(summary.statuses.failed)}`} />
        <StatusBadge status={summary.workflow_status} label={`Workflow ${summary.workflow_status}`} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <ReviewFact label="严重问题" value={formatCount(summary.issues.critical)} detail="必须阻断或强制修正" />
        <ReviewFact label="主要问题" value={formatCount(summary.issues.major)} detail="明显影响质量，需要优先处理" />
        <ReviewFact label="次要问题" value={formatCount(summary.issues.minor)} detail="可继续推进，但建议尽快清理" />
        <ReviewFact label="建议项" value={formatCount(summary.issues.suggestion)} detail="偏体验优化，不阻断主流程" />
      </div>
    </section>
  );
}

function ReviewTypesSection({ summary }: Readonly<{ summary: WorkflowReviewSummary }>) {
  return (
    <section className="panel-muted space-y-3 p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">审核类型拆分</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          用类型维度判断问题是集中在一致性、风格还是其它专项 reviewer。
        </p>
      </header>
      {summary.review_types.length > 0 ? (
        <div className="space-y-3">
          {summary.review_types.map((item) => (
            <div
              key={item.review_type}
              className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{formatReviewTypeLabel(item.review_type)}</p>
                  <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">
                    {formatCount(item.action_count)} 次动作
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status="passed" label={formatCount(item.statuses.passed)} />
                  <StatusBadge status="warning" label={formatCount(item.statuses.warning)} />
                  <StatusBadge status="failed" label={formatCount(item.statuses.failed)} />
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                共 {formatCount(item.issues.total)} 条问题，其中严重 {formatCount(item.issues.critical)}、主要{" "}
                {formatCount(item.issues.major)}、次要 {formatCount(item.issues.minor)}、建议{" "}
                {formatCount(item.issues.suggestion)}。
              </p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="暂无类型拆分" description="工作流暂无可归类的审核结果。" />
      )}
    </section>
  );
}

function ReviewActionsSection({ actions }: Readonly<{ actions: WorkflowReviewAction[] }>) {
  return (
    <section className="panel-muted space-y-3 p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">审核动作</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          按时间倒序查看 reviewer 输出，快速定位是哪一个节点、哪一种审核在持续报警。
        </p>
      </header>
      {actions.length > 0 ? (
        <div className="space-y-3">
          {actions.map((action) => (
            <ReviewActionCard key={action.id} action={action} />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无审核动作" description="工作流暂未产生审核记录。" />
      )}
    </section>
  );
}

function ReviewActionCard({ action }: Readonly<{ action: WorkflowReviewAction }>) {
  return (
    <div className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={action.status} label={formatReviewStatusLabel(action.status)} />
            <StatusBadge status="active" label={formatReviewTypeLabel(action.review_type)} />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">{formatNodeLabel(action)}</p>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              {formatReviewerLabel(action)} · 序列 {action.sequence} · {formatDateTime(action.created_at)}
            </p>
          </div>
        </div>
        <div className="text-right text-sm leading-6 text-[var(--text-secondary)]">
          <p>评分：{formatScore(action.score)}</p>
          <p>耗时：{formatExecutionTime(action.execution_time_ms)}</p>
          <p>Tokens：{formatTokensUsed(action.tokens_used)}</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-7 text-[var(--text-primary)]">{action.summary ?? "审核器未返回摘要。"}</p>
      {action.issues.length > 0 ? (
        <div className="mt-4 space-y-3 border-t border-[var(--line-soft)] pt-4">
          {action.issues.map((issue, index) => (
            <ReviewIssueCard key={`${action.id}-${issue.category}-${index}`} issue={issue} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ReviewIssueCard({ issue }: Readonly<{ issue: WorkflowReviewIssue }>) {
  const locationText = formatIssueLocation(issue);

  return (
    <div className="space-y-2 rounded-[18px] border border-[var(--line-soft)] bg-[rgba(247,244,238,0.86)] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={resolveIssueTone(issue.severity)} label={formatIssueSeverityLabel(issue.severity)} />
        <span className="text-sm font-medium text-[var(--text-primary)]">{formatIssueCategoryLabel(issue.category)}</span>
      </div>
      <p className="text-sm leading-6 text-[var(--text-primary)]">{issue.description}</p>
      {locationText ? <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">{locationText}</p> : null}
      {issue.location?.quoted_text ? (
        <p className="text-sm leading-6 text-[var(--text-secondary)]">摘录：{issue.location.quoted_text}</p>
      ) : null}
      {issue.evidence ? <p className="text-sm leading-6 text-[var(--text-secondary)]">依据：{issue.evidence}</p> : null}
      {issue.suggested_fix ? <p className="text-sm leading-6 text-[var(--text-secondary)]">建议：{issue.suggested_fix}</p> : null}
    </div>
  );
}

function ReviewMetricCard({
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

function ReviewFact({
  label,
  value,
  detail,
}: Readonly<{
  label: string;
  value: string;
  detail: string;
}>) {
  return (
    <div className="rounded-[18px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.58)] p-3">
      <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">{label}</p>
      <p className="mt-2 font-serif text-lg text-[var(--text-primary)]">{value}</p>
      <p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">{detail}</p>
    </div>
  );
}

function FeedbackMessage({
  tone,
  message,
}: Readonly<{
  tone: "danger" | "muted";
  message: string;
}>) {
  if (tone === "danger") {
    return <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">{message}</div>;
  }

  return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{message}</div>;
}
