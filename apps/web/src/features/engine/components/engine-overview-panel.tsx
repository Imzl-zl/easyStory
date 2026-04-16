"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { StatusBadge } from "@/components/ui/status-badge";
import type { NodeExecutionView, WorkflowExecution } from "@/lib/api/types";

import {
  buildEngineOverview,
  type EngineOverviewData,
  type EngineOverviewTimelineItem,
} from "./engine-overview-support";

type EngineOverviewPanelProps = {
  errorMessage: string | null;
  executions: NodeExecutionView[];
  isLoading: boolean;
  onOpenReplayExecution?: (executionId: string) => void;
  workflow: WorkflowExecution | null | undefined;
};

export function EngineOverviewPanel({
  errorMessage,
  executions,
  isLoading,
  onOpenReplayExecution,
  workflow,
}: Readonly<EngineOverviewPanelProps>) {
  if (!workflow) {
    return (
      <EmptyState
        title="暂无执行概览"
        description="载入工作流后查看。"
      />
    );
  }

  if (errorMessage && executions.length === 0) {
    return <FeedbackMessage tone="danger" message={errorMessage} />;
  }

  if (isLoading && executions.length === 0) {
    return <FeedbackMessage tone="muted" message="正在整理执行概览与节点时间线…" />;
  }

  const overview = buildEngineOverview(workflow, executions);
  if (!overview || overview.timeline.length === 0) {
    return (
      <EmptyState
        title="暂无节点时间线"
        description="工作流尚未定义节点或产生执行轨迹。"
      />
    );
  }

  return (
    <div className="space-y-4">
      {errorMessage ? <FeedbackMessage tone="danger" message={errorMessage} /> : null}
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        {overview.metrics.map((metric) => (
          <MetricCard key={metric.label} label={metric.label} value={metric.value} detail={metric.detail} />
        ))}
      </div>
      <TimelineSection overview={overview} onOpenReplayExecution={onOpenReplayExecution} />
    </div>
  );
}

function TimelineSection({
  onOpenReplayExecution,
  overview,
}: Readonly<{
  onOpenReplayExecution?: (executionId: string) => void;
  overview: EngineOverviewData;
}>) {
  return (
    <section className="panel-muted space-y-3 p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">节点时间线</h3>
        <p className="text-sm leading-6 text-text-secondary">
          节点执行状态总览。
        </p>
      </header>
      <div className="space-y-3">
        {overview.timeline.map((item, index) => (
          <TimelineItem
            key={item.key}
            item={item}
            isLast={index === overview.timeline.length - 1}
            onOpenReplayExecution={onOpenReplayExecution}
          />
        ))}
      </div>
    </section>
  );
}

function TimelineItem({
  isLast,
  item,
  onOpenReplayExecution,
}: Readonly<{
  isLast: boolean;
  item: EngineOverviewTimelineItem;
  onOpenReplayExecution?: (executionId: string) => void;
}>) {
  const latestExecutionId = item.latestExecutionId;

  return (
    <div className="grid gap-3 md:grid-cols-[20px_1fr]">
      <div className="flex flex-col items-center pt-2">
        <span className={`h-3 w-3 rounded-full ${resolveTimelineDotClass(item.statusTone)}`} />
        {!isLast ? (
          <span className="mt-2 h-full w-px bg-line-strong" />
        ) : null}
      </div>
      <div className="rounded-2xl bg-muted shadow-sm p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={item.statusTone} label={item.statusLabel} />
              {item.badges.map((badge) => (
                <StatusBadge key={`${item.key}-${badge.label}`} status={badge.status} label={badge.label} />
              ))}
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">{item.title}</p>
              <p className="text-sm leading-6 text-text-secondary">{item.subtitle}</p>
            </div>
          </div>
          <p className="text-right text-sm leading-6 text-text-secondary">
            {item.timeDetail}
          </p>
        </div>
        <p className="mt-3 text-sm leading-6 text-text-secondary">{item.detail}</p>
        {latestExecutionId && onOpenReplayExecution ? (
          <div className="mt-4">
            <button
              className="ink-button-secondary"
              onClick={() => onOpenReplayExecution(latestExecutionId)}
              type="button"
            >
              查看最新 Prompt 回放
            </button>
          </div>
        ) : null}
        {item.errorMessage ? (
          <div className="mt-4 rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm leading-6 text-accent-danger">
            {item.errorMessage}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function FeedbackMessage({
  message,
  tone,
}: Readonly<{
  message: string;
  tone: "danger" | "muted";
}>) {
  if (tone === "danger") {
    return (
      <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
        {message}
      </div>
    );
  }

  return <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{message}</div>;
}

function resolveTimelineDotClass(status: EngineOverviewTimelineItem["statusTone"]): string {
  switch (status) {
    case "completed":
      return "bg-accent-success";
    case "failed":
      return "bg-accent-danger";
    case "warning":
    case "stale":
      return "bg-accent-warning";
    case "active":
      return "bg-accent-primary";
    default:
      return "bg-text-secondary";
  }
}
