"use client";

import { EmptyState } from "@/components/ui/empty-state";
import type { ExecutionLogView, NodeExecutionView } from "@/lib/api/types";

import {
  formatCount,
  formatDateTime,
  formatDuration,
  formatExecutionStatusLabel,
  formatLogLevelLabel,
  formatShortId,
  resolveExecutionTone,
  resolveLogLevelTone,
} from "./engine-logs-format";
import {
  buildEngineLogsSummary,
  formatDetailValue,
} from "./engine-logs-panel-support";

type EngineLogsPanelProps = {
  executions: NodeExecutionView[];
  logs: ExecutionLogView[];
  isLoading: boolean;
  errorMessage: string | null;
  onOpenReplayExecution?: (executionId: string) => void;
};

export function EngineLogsPanel({
  executions,
  logs,
  isLoading,
  errorMessage,
  onOpenReplayExecution,
}: EngineLogsPanelProps) {
  if (errorMessage && executions.length === 0 && logs.length === 0) {
    return <FeedbackMessage tone="danger" message={errorMessage} />;
  }

  if (isLoading && executions.length === 0 && logs.length === 0) {
    return <FeedbackMessage tone="muted" message="正在整理节点执行轨迹和日志事件…" />;
  }

  if (executions.length === 0 && logs.length === 0) {
    return (
      <EmptyState
        title="暂无执行日志"
        description="载入工作流后查看。"
      />
    );
  }

  const summary = buildEngineLogsSummary(executions, logs);

  return (
    <div className="space-y-3">
      {errorMessage ? <FeedbackMessage tone="danger" message={errorMessage} /> : null}
      <div className="grid gap-2 grid-cols-2 md:grid-cols-4">
        <MetricItem label="节点执行" value={formatCount(executions.length)} detail={`进行中 ${formatCount(summary.activeExecutionCount)}，失败 ${formatCount(summary.failedExecutionCount)}`} />
        <MetricItem label="事件日志" value={formatCount(logs.length)} detail="运行记录总数" />
        <MetricItem label="最新活动" value={formatDateTime(summary.latestActivityAt)} detail="按完成时间统计" />
        <MetricItem label="已落审查" value={formatCount(summary.reviewCount)} detail={`关联 artifacts ${formatCount(summary.artifactCount)}`} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <ExecutionSection
          executions={summary.orderedExecutions}
          onOpenReplayExecution={onOpenReplayExecution}
        />
        <ExecutionLogSection logs={summary.orderedLogs} />
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

function ExecutionSection({
  executions,
  onOpenReplayExecution,
}: Readonly<{
  executions: NodeExecutionView[];
  onOpenReplayExecution?: (executionId: string) => void;
}>) {
  return (
    <section className="space-y-2">
      <h3 className="text-[12px] font-medium" style={{ color: "var(--text-tertiary)" }}>节点执行</h3>
      {executions.length > 0 ? (
        <div className="space-y-2">
          {executions.map((execution) => (
            <ExecutionCard key={execution.id} execution={execution} onOpenReplayExecution={onOpenReplayExecution} />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无节点执行" description="工作流尚未产生节点执行记录。" />
      )}
    </section>
  );
}

function ExecutionCard({
  execution,
  onOpenReplayExecution,
}: Readonly<{
  execution: NodeExecutionView;
  onOpenReplayExecution?: (executionId: string) => void;
}>) {
  return (
    <div className="rounded p-3" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <StatusPill tone={resolveExecutionTone(execution.status)} label={formatExecutionStatusLabel(execution.status)} />
            <StatusPill tone="active" label={execution.node_type} />
          </div>
          <div>
            <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
              {execution.node_id} · 序列 {execution.sequence}
            </p>
            <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
              开始 {formatDateTime(execution.started_at)} · 完成 {formatDateTime(execution.completed_at)}
            </p>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{formatShortId(execution.id)}</p>
          <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{formatDuration(execution.execution_time_ms)}</p>
        </div>
      </div>
      <div className="mt-2 grid gap-2 grid-cols-4">
        <MiniMetric label="产物" value={formatCount(execution.artifacts.length)} />
        <MiniMetric label="审核" value={formatCount(execution.review_actions.length)} />
        <MiniMetric label="输入" value={formatCount(Object.keys(execution.input_summary).length)} />
        <MiniMetric label="输出" value={execution.output_data ? "已产出" : execution.context_report ? "上下文" : "暂无"} />
      </div>
      {onOpenReplayExecution ? (
        <div className="mt-2">
          <button
            className="px-3 py-1.5 rounded text-[11px] font-medium transition-colors"
            style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
            onClick={() => onOpenReplayExecution(execution.id)}
            type="button"
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "var(--bg-muted)";
              e.currentTarget.style.color = "var(--text-primary)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "var(--bg-surface)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }}
          >
            查看 Prompt 回放
          </button>
        </div>
      ) : null}
      {execution.error_message ? (
        <div className="mt-2 rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
          {execution.error_message}
        </div>
      ) : null}
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

function ExecutionLogSection({ logs }: Readonly<{ logs: ExecutionLogView[] }>) {
  return (
    <section className="space-y-2">
      <h3 className="text-[12px] font-medium" style={{ color: "var(--text-tertiary)" }}>日志事件</h3>
      {logs.length > 0 ? (
        <div className="space-y-2">
          {logs.map((log) => (
            <ExecutionLogCard key={log.id} log={log} />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无日志事件" description="工作流暂无可展示的执行日志。" />
      )}
    </section>
  );
}

function ExecutionLogCard({ log }: Readonly<{ log: ExecutionLogView }>) {
  const detailEntries = log.details ? Object.entries(log.details) : [];

  return (
    <div className="rounded p-3" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 min-w-0">
          <StatusPill tone={resolveLogLevelTone(log.level)} label={formatLogLevelLabel(log.level)} />
          <span className="text-[12px] font-medium truncate" style={{ color: "var(--text-primary)" }}>{log.message}</span>
        </div>
        <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-tertiary)" }}>{formatDateTime(log.created_at)}</span>
      </div>
      <p className="mt-1.5 text-[10px]" style={{ color: "var(--text-tertiary)" }}>
        node execution {formatShortId(log.node_execution_id)}
      </p>
      {detailEntries.length > 0 ? (
        <div className="mt-2 grid gap-2 grid-cols-2">
          {detailEntries.map(([key, value]) => (
            <div
              key={`${log.id}-${key}`}
              className="rounded px-2.5 py-2"
              style={{ background: "var(--bg-muted)" }}
            >
              <p className="text-[9px]" style={{ color: "var(--text-tertiary)" }}>{key}</p>
              <p className="mt-0.5 break-all text-[11px]" style={{ color: "var(--text-secondary)" }}>
                {formatDetailValue(value)}
              </p>
            </div>
          ))}
        </div>
      ) : null}
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
      <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
        {message}
      </div>
    );
  }

  return <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}>{message}</div>;
}
