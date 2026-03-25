"use client";

import { EmptyState } from "@/components/ui/empty-state";
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
        description="先载入一个 workflow，日志面板才会显示节点执行轨迹和 runtime 事件。"
      />
    );
  }

  const summary = buildEngineLogsSummary(executions, logs);

  return (
    <div className="space-y-4">
      {errorMessage ? <FeedbackMessage tone="danger" message={errorMessage} /> : null}
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <LogsMetricCard
          label="节点执行"
          value={formatCount(executions.length)}
          detail={`进行中 ${formatCount(summary.activeExecutionCount)}，失败 ${formatCount(summary.failedExecutionCount)}`}
        />
        <LogsMetricCard
          label="事件日志"
          value={formatCount(logs.length)}
          detail="含 workflow 级与 node 级 runtime 记录"
        />
        <LogsMetricCard
          label="最新活动"
          value={formatDateTime(summary.latestActivityAt)}
          detail="按 execution 完成时间与日志时间共同判断"
        />
        <LogsMetricCard
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
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          先看每个节点现在处于什么状态、跑了多久、是否已经沉淀 artifact 和 review 结果。
        </p>
      </header>
      {executions.length > 0 ? (
        <div className="space-y-3">
          {executions.map((execution) => (
            <ExecutionCard key={execution.id} execution={execution} onOpenReplayExecution={onOpenReplayExecution} />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无节点执行" description="当前 workflow 还没有落库的 node execution 记录。" />
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
    <div className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4">
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
            <p className="text-sm font-medium text-[var(--text-primary)]">
              {execution.node_id} · 序列 {execution.sequence} · 排序 {execution.node_order}
            </p>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              开始 {formatDateTime(execution.started_at)} · 完成 {formatDateTime(execution.completed_at)}
            </p>
          </div>
        </div>
        <div className="text-right text-sm leading-6 text-[var(--text-secondary)]">
          <p>执行 ID：{formatShortId(execution.id)}</p>
          <p>耗时：{formatDuration(execution.execution_time_ms)}</p>
          <p>重试：{formatCount(execution.retry_count)}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <ExecutionMetric label="Artifacts" value={formatCount(execution.artifacts.length)} />
        <ExecutionMetric label="Reviews" value={formatCount(execution.review_actions.length)} />
        <ExecutionMetric label="输入字段" value={formatCount(Object.keys(execution.input_summary).length)} />
        <ExecutionMetric
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
        <div className="mt-4 rounded-[18px] bg-[rgba(178,65,46,0.1)] px-4 py-3 text-sm leading-6 text-[var(--accent-danger)]">
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
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          按时间倒序查看 runtime 记录，快速定位哪个节点开始、跳过或失败。
        </p>
      </header>
      {logs.length > 0 ? (
        <div className="space-y-3">
          {logs.map((log) => (
            <ExecutionLogCard key={log.id} log={log} />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无日志事件" description="当前 workflow 还没有可展示的 execution log。" />
      )}
    </section>
  );
}

function ExecutionLogCard({ log }: Readonly<{ log: ExecutionLogView }>) {
  const detailEntries = log.details ? Object.entries(log.details) : [];

  return (
    <div className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.62)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={resolveLogLevelTone(log.level)} label={formatLogLevelLabel(log.level)} />
          <span className="text-sm font-medium text-[var(--text-primary)]">{log.message}</span>
        </div>
        <span className="text-sm text-[var(--text-secondary)]">{formatDateTime(log.created_at)}</span>
      </div>
      <p className="mt-3 text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">
        node execution {formatShortId(log.node_execution_id)}
      </p>
      {detailEntries.length > 0 ? (
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {detailEntries.map(([key, value]) => (
            <div
              key={`${log.id}-${key}`}
              className="rounded-[16px] border border-[var(--line-soft)] bg-[rgba(247,244,238,0.86)] px-3 py-2"
            >
              <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">{key}</p>
              <p className="mt-1 break-all text-sm leading-6 text-[var(--text-primary)]">
                {formatDetailValue(value)}
              </p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function LogsMetricCard({
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

function ExecutionMetric({
  label,
  value,
}: Readonly<{
  label: string;
  value: string;
}>) {
  return (
    <div className="rounded-[18px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.58)] p-3">
      <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">{label}</p>
      <p className="mt-2 font-serif text-lg text-[var(--text-primary)]">{value}</p>
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
