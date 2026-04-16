"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { StatusBadge } from "@/components/ui/status-badge";
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
    <div className="space-y-4">
      {errorMessage ? <FeedbackMessage tone="danger" message={errorMessage} /> : null}
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <MetricCard
          label="节点执行"
          value={formatCount(executions.length)}
          detail={`进行中 ${formatCount(summary.activeExecutionCount)}，失败 ${formatCount(summary.failedExecutionCount)}`}
        />
        <MetricCard
          label="事件日志"
          value={formatCount(logs.length)}
          detail="运行记录总数"
        />
        <MetricCard
          label="最新活动"
          value={formatDateTime(summary.latestActivityAt)}
          detail="按完成时间统计"
        />
        <MetricCard
          label="已落审查"
          value={formatCount(summary.reviewCount)}
          detail={`关联 artifacts ${formatCount(summary.artifactCount)}`}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <ExecutionSection
          executions={summary.orderedExecutions}
          onOpenReplayExecution={onOpenReplayExecution}
        />
        <ExecutionLogSection logs={summary.orderedLogs} />
      </div>
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
    <section className="panel-muted space-y-3 p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">节点执行</h3>
        <p className="text-sm leading-6 text-text-secondary">
          节点执行状态与产出。
        </p>
      </header>
      {executions.length > 0 ? (
        <div className="space-y-3">
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
    <div className="rounded-2xl bg-muted shadow-sm p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              status={resolveExecutionTone(execution.status)}
              label={formatExecutionStatusLabel(execution.status)}
            />
            <StatusBadge status="active" label={execution.node_type} />
          </div>
          <div>
            <p className="text-sm font-medium text-text-primary">
              {execution.node_id} · 序列 {execution.sequence} · 排序 {execution.node_order}
            </p>
            <p className="text-sm leading-6 text-text-secondary">
              开始 {formatDateTime(execution.started_at)} · 完成 {formatDateTime(execution.completed_at)}
            </p>
          </div>
        </div>
        <div className="text-right text-sm leading-6 text-text-secondary">
          <p>执行 ID：{formatShortId(execution.id)}</p>
          <p>耗时：{formatDuration(execution.execution_time_ms)}</p>
          <p>重试：{formatCount(execution.retry_count)}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <MetricCard label="产物" value={formatCount(execution.artifacts.length)} />
        <MetricCard label="审核" value={formatCount(execution.review_actions.length)} />
        <MetricCard label="输入字段" value={formatCount(Object.keys(execution.input_summary).length)} />
        <MetricCard
          label="输出状态"
          value={execution.output_data ? "已产出" : execution.context_report ? "上下文已记录" : "暂无"}
        />
      </div>
      {onOpenReplayExecution ? (
        <div className="mt-4">
          <button
            className="ink-button-secondary"
            onClick={() => onOpenReplayExecution(execution.id)}
            type="button"
          >
            查看 Prompt 回放
          </button>
        </div>
      ) : null}
      {execution.error_message ? (
        <div className="mt-4 rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm leading-6 text-accent-danger">
          {execution.error_message}
        </div>
      ) : null}
    </div>
  );
}

function ExecutionLogSection({ logs }: Readonly<{ logs: ExecutionLogView[] }>) {
  return (
    <section className="panel-muted space-y-3 p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">日志事件</h3>
        <p className="text-sm leading-6 text-text-secondary">
          按时间查看运行记录。
        </p>
      </header>
      {logs.length > 0 ? (
        <div className="space-y-3">
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
    <div className="rounded-2xl bg-muted shadow-sm p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={resolveLogLevelTone(log.level)} label={formatLogLevelLabel(log.level)} />
          <span className="text-sm font-medium text-text-primary">{log.message}</span>
        </div>
        <span className="text-sm text-text-secondary">{formatDateTime(log.created_at)}</span>
      </div>
      <p className="mt-3 text-xs uppercase tracking-[0.12em] text-text-secondary">
        node execution {formatShortId(log.node_execution_id)}
      </p>
      {detailEntries.length > 0 ? (
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {detailEntries.map(([key, value]) => (
            <div
              key={`${log.id}-${key}`}
              className="rounded-2xl bg-muted shadow-sm px-3 py-2"
            >
              <p className="text-xs uppercase tracking-[0.12em] text-text-secondary">{key}</p>
              <p className="mt-1 break-all text-sm leading-6 text-text-primary">
                {formatDetailValue(value)}
              </p>
            </div>
          ))}
        </div>
      ) : null}
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
    return <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">{message}</div>;
  }

  return <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{message}</div>;
}
