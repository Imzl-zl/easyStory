"use client";

import { EmptyState } from "@/components/ui/empty-state";
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
    <div className="space-y-3">
      {errorMessage ? <FeedbackMessage tone="danger" message={errorMessage} /> : null}
      <div className="grid gap-2 grid-cols-2 md:grid-cols-4">
        {overview.metrics.map((metric) => (
          <MetricItem key={metric.label} label={metric.label} value={metric.value} detail={metric.detail} />
        ))}
      </div>
      <TimelineSection overview={overview} onOpenReplayExecution={onOpenReplayExecution} />
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

function TimelineSection({
  onOpenReplayExecution,
  overview,
}: Readonly<{
  onOpenReplayExecution?: (executionId: string) => void;
  overview: EngineOverviewData;
}>) {
  return (
    <section className="space-y-2">
      <h3 className="text-[12px] font-medium" style={{ color: "#6b7280" }}>节点时间线</h3>
      <div className="space-y-2">
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
    <div className="flex gap-3">
      <div className="flex flex-col items-center pt-1.5">
        <span
          className="h-2 w-2 rounded-full flex-shrink-0"
          style={{ background: resolveTimelineDotColor(item.statusTone) }}
        />
        {!isLast ? (
          <span className="mt-1.5 w-px flex-1" style={{ background: "#2a2f35" }} />
        ) : null}
      </div>
      <div className="flex-1 rounded p-3 mb-2" style={{ background: "#111418", border: "1px solid #1f2328" }}>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <StatusPill tone={item.statusTone} label={item.statusLabel} />
              {item.badges.map((badge) => (
                <StatusPill key={`${item.key}-${badge.label}`} tone={badge.status} label={badge.label} />
              ))}
            </div>
            <div>
              <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>{item.title}</p>
              <p className="text-[11px]" style={{ color: "#6b7280" }}>{item.subtitle}</p>
            </div>
          </div>
          <p className="text-[11px] flex-shrink-0" style={{ color: "#4b5563" }}>
            {item.timeDetail}
          </p>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed" style={{ color: "#6b7280" }}>{item.detail}</p>
        {latestExecutionId && onOpenReplayExecution ? (
          <div className="mt-2">
            <button
              className="px-3 py-1.5 rounded text-[11px] font-medium transition-colors"
              style={{ background: "#1f2328", color: "#9ca3af" }}
              onClick={() => onOpenReplayExecution(latestExecutionId)}
              type="button"
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#2a2f35";
                e.currentTarget.style.color = "#e8e6e3";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "#1f2328";
                e.currentTarget.style.color = "#9ca3af";
              }}
            >
              查看 Prompt 回放
            </button>
          </div>
        ) : null}
        {item.errorMessage ? (
          <div className="mt-2 rounded px-3 py-2 text-[11px]" style={{ background: "rgba(220, 38, 38, 0.08)", color: "#f87171" }}>
            {item.errorMessage}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StatusPill({ tone, label }: { tone: string; label: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "rgba(34, 197, 94, 0.12)", text: "#4ade80" },
    failed: { bg: "rgba(220, 38, 38, 0.12)", text: "#f87171" },
    warning: { bg: "rgba(234, 179, 8, 0.12)", text: "#fbbf24" },
    stale: { bg: "rgba(234, 179, 8, 0.12)", text: "#fbbf24" },
    active: { bg: "rgba(232, 184, 109, 0.12)", text: "#e8b86d" },
    outline: { bg: "#1f2328", text: "#9ca3af" },
    draft: { bg: "#1f2328", text: "#6b7280" },
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
  message,
  tone,
}: Readonly<{
  message: string;
  tone: "danger" | "muted";
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

function resolveTimelineDotColor(status: EngineOverviewTimelineItem["statusTone"]): string {
  switch (status) {
    case "completed":
      return "#22c55e";
    case "failed":
      return "#dc2626";
    case "warning":
    case "stale":
      return "#eab308";
    case "active":
      return "#e8b86d";
    default:
      return "#6b7280";
  }
}
