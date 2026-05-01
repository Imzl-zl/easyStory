"use client";

import { useState } from "react";

import { AppSelect } from "@/components/ui/app-select";
import { EmptyState } from "@/components/ui/empty-state";
import type { NodeExecutionView, PromptReplayView } from "@/lib/api/types";

import { formatDateTime, formatDuration, formatExecutionStatusLabel, formatShortId, resolveExecutionTone } from "./engine-logs-format";
import { formatReplayExecutionOptionLabel, formatReplayTokenUsage, formatReplayTypeLabel, resolveReplayDetailState, resolveReplayGateState, sortPromptReplays } from "./engine-replay-support";

type EngineReplayPanelProps = {
  isWorkflowReady: boolean;
  executions: NodeExecutionView[];
  selectedExecutionId: string;
  onSelectExecutionId: (value: string) => void;
  selectedExecution: NodeExecutionView | null;
  replays: PromptReplayView[];
  isExecutionsLoading: boolean;
  isReplaysLoading: boolean;
  executionsErrorMessage: string | null;
  replaysErrorMessage: string | null;
};

export function EngineReplayPanel({
  isWorkflowReady,
  executions,
  selectedExecutionId,
  onSelectExecutionId,
  selectedExecution,
  replays,
  isExecutionsLoading,
  isReplaysLoading,
  executionsErrorMessage,
  replaysErrorMessage,
}: EngineReplayPanelProps) {
  const gateState = resolveReplayGateState({
    executionCount: executions.length,
    executionsErrorMessage,
    isExecutionsLoading,
    isWorkflowReady,
  });
  if (gateState !== "ready") return <ReplayGateStateView gateState={gateState} errorMessage={executionsErrorMessage} />;
  const activeExecutionId = selectedExecution?.id ?? selectedExecutionId;
  const detailState = resolveReplayDetailState({
    replayCount: replays.length,
    replaysErrorMessage,
    selectedExecutionId: activeExecutionId,
    isReplaysLoading,
  });

  return (
    <div className="space-y-3">
      {executionsErrorMessage ? <FeedbackMessage tone="danger" message={executionsErrorMessage} /> : null}
      <ReplaySelection
        executions={executions}
        selectedExecutionId={selectedExecutionId}
        onSelectExecutionId={onSelectExecutionId}
      />
      {selectedExecution ? <ReplayExecutionSummary execution={selectedExecution} /> : null}
      {replaysErrorMessage && detailState === "ready" ? <FeedbackMessage tone="danger" message={replaysErrorMessage} /> : null}
      <ReplayDetailStateView detailState={detailState} errorMessage={replaysErrorMessage} replays={sortPromptReplays(replays)} />
    </div>
  );
}

function ReplayGateStateView({
  gateState,
  errorMessage,
}: Readonly<{
  gateState: ReturnType<typeof resolveReplayGateState>;
  errorMessage: string | null;
}>) {
  if (gateState === "workflow-empty") {
    return (
      <EmptyState
        title="尚未载入工作流"
        description="启动工作流后查看。"
      />
    );
  }
  if (gateState === "executions-error") {
    return <FeedbackMessage tone="danger" message={errorMessage ?? "节点执行加载失败。"} />;
  }
  if (gateState === "executions-loading") {
    return <FeedbackMessage tone="muted" message="正在整理可回放的 node execution…" />;
  }
  return (
    <EmptyState
      title="暂无可回放节点"
      description="工作流尚未产生可回放的节点执行。"
    />
  );
}

function ReplaySelection({
  executions,
  selectedExecutionId,
  onSelectExecutionId,
}: Readonly<{
  executions: NodeExecutionView[];
  selectedExecutionId: string;
  onSelectExecutionId: (value: string) => void;
}>) {
  return (
    <label className="block space-y-1.5">
      <span className="text-[11px] font-medium" style={{ color: "#6b7280" }}>选择节点执行记录</span>
      <AppSelect
        options={[
          { label: "先选择一个节点", value: "" },
          ...executions.map((execution) => ({
            label: formatReplayExecutionOptionLabel(execution),
            value: execution.id,
          })),
        ]}
        value={selectedExecutionId}
        onChange={onSelectExecutionId}
      />
    </label>
  );
}

function ReplayExecutionSummary({
  execution,
}: Readonly<{ execution: NodeExecutionView }>) {
  return (
    <div className="rounded p-3" style={{ background: "#111418", border: "1px solid #1f2328" }}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <StatusPill tone={resolveExecutionTone(execution.status)} label={formatExecutionStatusLabel(execution.status)} />
            <StatusPill tone="active" label={execution.node_type} />
          </div>
          <div>
            <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>
              {execution.node_id} · 序列 {execution.sequence}
            </p>
            <p className="text-[11px]" style={{ color: "#6b7280" }}>
              开始 {formatDateTime(execution.started_at)} · 完成 {formatDateTime(execution.completed_at)}
            </p>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-[11px]" style={{ color: "#4b5563" }}>{formatShortId(execution.id)}</p>
          <p className="text-[11px]" style={{ color: "#4b5563" }}>{formatDuration(execution.execution_time_ms)}</p>
        </div>
      </div>
      {execution.error_message ? (
        <div className="mt-2 rounded px-3 py-2 text-[11px]" style={{ background: "rgba(220, 38, 38, 0.08)", color: "#f87171" }}>
          {execution.error_message}
        </div>
      ) : null}
    </div>
  );
}

function ReplayDetailStateView({
  detailState,
  errorMessage,
  replays,
}: Readonly<{
  detailState: ReturnType<typeof resolveReplayDetailState>;
  errorMessage: string | null;
  replays: PromptReplayView[];
}>) {
  if (detailState === "selection-required") {
    return (
      <EmptyState
        title="等待选择节点"
        description="选择节点查看 Prompt。"
      />
    );
  }
  if (detailState === "replays-error") {
    return <FeedbackMessage tone="danger" message={errorMessage ?? "Prompt 回放加载失败。"} />;
  }
  if (detailState === "replays-loading") {
    return <FeedbackMessage tone="muted" message="正在加载该节点的 Prompt 回放…" />;
  }
  if (detailState === "replays-empty") {
    return (
      <EmptyState
        title="暂无提示词回放"
        description="该节点暂无 Prompt 记录。"
      />
    );
  }
  return (
    <div className="space-y-2">
      {replays.map((replay, index) => (
        <ReplayCard key={replay.id} replay={replay} index={index} />
      ))}
    </div>
  );
}

function ReplayCard({
  replay,
  index,
}: Readonly<{
  replay: PromptReplayView;
  index: number;
}>) {
  return (
    <div className="rounded" style={{ background: "#111418", border: "1px solid #1f2328" }}>
      <div className="p-3 flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "#1f2328", color: "#9ca3af" }}>#{index + 1}</span>
            <StatusPill tone="draft" label={formatReplayTypeLabel(replay.replay_type)} />
          </div>
          <div>
            <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>{replay.model_name}</p>
            <p className="text-[11px]" style={{ color: "#6b7280" }}>
              {formatReplayTokenUsage(replay)} · {formatDateTime(replay.created_at)}
            </p>
          </div>
        </div>
        <p className="text-[11px] flex-shrink-0" style={{ color: "#4b5563" }}>
          {formatShortId(replay.id)}
        </p>
      </div>
      <ReplayTextDisclosure title="提示词" value={replay.prompt_text} defaultOpen />
      <ReplayTextDisclosure title="响应" value={replay.response_text ?? "模型未返回文本响应。"} />
    </div>
  );
}

function ReplayTextDisclosure({
  title,
  value,
  defaultOpen = false,
}: Readonly<{
  title: string;
  value: string;
  defaultOpen?: boolean;
}>) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details
      className="border-t"
      style={{ borderColor: "#1f2328" }}
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-medium flex items-center justify-between" style={{ color: "#9ca3af" }}>
        <span>{title}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </summary>
      <div className="px-3 pb-3">
        <pre className="whitespace-pre-wrap break-words text-[11px] leading-relaxed" style={{ color: "#9ca3af" }}>{value}</pre>
      </div>
    </details>
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
