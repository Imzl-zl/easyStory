"use client";

import { EmptyState } from "@/components/ui/empty-state";
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
        description="载入工作流后查看。"
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2 grid-cols-2 md:grid-cols-4">
        <MetricItem label="审核节点" value={formatCount(summary.reviewed_node_count)} detail={`覆盖 ${formatCount(summary.total_actions)} 次审核动作`} />
        <MetricItem label="问题总数" value={formatCount(summary.issues.total)} detail={`严重/主要 ${formatCount(summary.issues.critical + summary.issues.major)}，次要/建议 ${formatCount(summary.issues.minor + summary.issues.suggestion)}`} />
        <MetricItem label="通过情况" value={`${formatCount(summary.statuses.passed)} / ${formatCount(summary.total_actions)}`} detail={`警告 ${formatCount(summary.statuses.warning)}，失败 ${formatCount(summary.statuses.failed)}`} />
        <MetricItem label="最近审核" value={formatDateTime(summary.last_reviewed_at)} detail={`工作流状态：${summary.workflow_status}`} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-3">
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
    <div className="space-y-2">
      <h3 className="text-[12px] font-medium" style={{ color: "#6b7280" }}>审核总览</h3>
      <div className="rounded p-3 space-y-3" style={{ background: "#111418", border: "1px solid #1f2328" }}>
        <div className="flex flex-wrap gap-1.5">
          <StatusPill tone="completed" label={`通过 ${formatCount(summary.statuses.passed)}`} />
          <StatusPill tone="warning" label={`警告 ${formatCount(summary.statuses.warning)}`} />
          <StatusPill tone="failed" label={`失败 ${formatCount(summary.statuses.failed)}`} />
          <StatusPill tone="outline" label={`Workflow ${summary.workflow_status}`} />
        </div>
        <div className="grid gap-2 grid-cols-2">
          <MiniMetric label="严重问题" value={formatCount(summary.issues.critical)} detail="必须阻断或强制修正" />
          <MiniMetric label="主要问题" value={formatCount(summary.issues.major)} detail="明显影响质量，需要优先处理" />
          <MiniMetric label="次要问题" value={formatCount(summary.issues.minor)} detail="可继续推进，但建议尽快清理" />
          <MiniMetric label="建议项" value={formatCount(summary.issues.suggestion)} detail="偏体验优化，不阻断主流程" />
        </div>
      </div>
    </div>
  );
}

function ReviewTypesSection({ summary }: Readonly<{ summary: WorkflowReviewSummary }>) {
  return (
    <div className="space-y-2">
      <h3 className="text-[12px] font-medium" style={{ color: "#6b7280" }}>审核类型拆分</h3>
      {summary.review_types.length > 0 ? (
        <div className="space-y-2">
          {summary.review_types.map((item) => (
            <div key={item.review_type} className="rounded p-3" style={{ background: "#111418", border: "1px solid #1f2328" }}>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>{formatReviewTypeLabel(item.review_type)}</p>
                  <p className="text-[10px]" style={{ color: "#4b5563" }}>
                    {formatCount(item.action_count)} 次动作
                  </p>
                </div>
                <div className="flex flex-wrap gap-1">
                  <StatusPill tone="completed" label={formatCount(item.statuses.passed)} />
                  <StatusPill tone="warning" label={formatCount(item.statuses.warning)} />
                  <StatusPill tone="failed" label={formatCount(item.statuses.failed)} />
                </div>
              </div>
              <p className="mt-2 text-[11px]" style={{ color: "#6b7280" }}>
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
    </div>
  );
}

function ReviewActionsSection({ actions }: Readonly<{ actions: WorkflowReviewAction[] }>) {
  return (
    <div className="space-y-2">
      <h3 className="text-[12px] font-medium" style={{ color: "#6b7280" }}>审核动作</h3>
      {actions.length > 0 ? (
        <div className="space-y-2">
          {actions.map((action) => (
            <ReviewActionCard key={action.id} action={action} />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无审核动作" description="工作流暂未产生审核记录。" />
      )}
    </div>
  );
}

function ReviewActionCard({ action }: Readonly<{ action: WorkflowReviewAction }>) {
  return (
    <div className="rounded p-3" style={{ background: "#111418", border: "1px solid #1f2328" }}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <StatusPill tone={action.status} label={formatReviewStatusLabel(action.status)} />
            <StatusPill tone="active" label={formatReviewTypeLabel(action.review_type)} />
          </div>
          <div>
            <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>{formatNodeLabel(action)}</p>
            <p className="text-[11px]" style={{ color: "#6b7280" }}>
              {formatReviewerLabel(action)} · 序列 {action.sequence} · {formatDateTime(action.created_at)}
            </p>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-[11px]" style={{ color: "#4b5563" }}>评分：{formatScore(action.score)}</p>
          <p className="text-[11px]" style={{ color: "#4b5563" }}>耗时：{formatExecutionTime(action.execution_time_ms)}</p>
          <p className="text-[11px]" style={{ color: "#4b5563" }}>Tokens：{formatTokensUsed(action.tokens_used)}</p>
        </div>
      </div>
      <p className="mt-2 text-[12px] leading-relaxed" style={{ color: "#9ca3af" }}>{action.summary ?? "审核器未返回摘要。"}</p>
      {action.issues.length > 0 ? (
        <div className="mt-3 space-y-2 pt-3" style={{ borderTop: "1px solid #1f2328" }}>
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
    <div className="rounded p-2.5" style={{ background: "#1a1d23" }}>
      <div className="flex flex-wrap items-center gap-1.5 mb-1">
        <StatusPill tone={resolveIssueTone(issue.severity)} label={formatIssueSeverityLabel(issue.severity)} />
        <span className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>{formatIssueCategoryLabel(issue.category)}</span>
      </div>
      <p className="text-[11px]" style={{ color: "#9ca3af" }}>{issue.description}</p>
      {locationText ? <p className="text-[10px] mt-1" style={{ color: "#4b5563" }}>{locationText}</p> : null}
      {issue.location?.quoted_text ? (
        <p className="text-[11px] mt-1" style={{ color: "#6b7280" }}>摘录：{issue.location.quoted_text}</p>
      ) : null}
      {issue.evidence ? <p className="text-[11px] mt-1" style={{ color: "#6b7280" }}>依据：{issue.evidence}</p> : null}
      {issue.suggested_fix ? <p className="text-[11px] mt-1" style={{ color: "#6b7280" }}>建议：{issue.suggested_fix}</p> : null}
    </div>
  );
}

function MetricItem({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded p-3" style={{ background: "#111418", border: "1px solid #1f2328" }}>
      <p className="text-[10px] mb-1" style={{ color: "#4b5563" }}>{label}</p>
      <p className="text-[14px] font-semibold" style={{ color: "#e8e6e3" }}>{value}</p>
      {detail ? <p className="text-[10px] mt-0.5" style={{ color: "#4b5563" }}>{detail}</p> : null}
    </div>
  );
}

function MiniMetric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded p-2" style={{ background: "#1a1d23" }}>
      <p className="text-[9px] mb-0.5" style={{ color: "#4b5563" }}>{label}</p>
      <p className="text-[12px] font-medium" style={{ color: "#9ca3af" }}>{value}</p>
      {detail ? <p className="text-[9px] mt-0.5" style={{ color: "#4b5563" }}>{detail}</p> : null}
    </div>
  );
}

function StatusPill({ tone, label }: { tone: string; label: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "rgba(34, 197, 94, 0.12)", text: "#4ade80" },
    failed: { bg: "rgba(220, 38, 38, 0.12)", text: "#f87171" },
    warning: { bg: "rgba(234, 179, 8, 0.12)", text: "#fbbf24" },
    active: { bg: "rgba(232, 184, 109, 0.12)", text: "#e8b86d" },
    outline: { bg: "#1f2328", text: "#9ca3af" },
    draft: { bg: "#1f2328", text: "#6b7280" },
    passed: { bg: "rgba(34, 197, 94, 0.12)", text: "#4ade80" },
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

function FeedbackMessage({
  tone,
  message,
}: Readonly<{
  tone: "danger" | "muted";
  message: string;
}>) {
  if (tone === "danger") {
    return (
      <div className="rounded px-3 py-2 text-[11px]" style={{ background: "rgba(220, 38, 38, 0.08)", color: "#f87171" }}>
        {message}
      </div>
    );
  }

  return <div className="rounded px-3 py-2 text-[11px]" style={{ background: "#1f2328", color: "#6b7280" }}>{message}</div>;
}
