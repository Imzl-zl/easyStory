"use client";

import { useState } from "react";

import { AppSelect } from "@/components/ui/app-select";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
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
    <div className="space-y-4">
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
    <label className="block space-y-2">
      <span className="label-text">选择节点执行记录</span>
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
      <p className="text-sm leading-6 text-text-secondary">
        选择一个节点查看提示词与回复。
      </p>
    </label>
  );
}

function ReplayExecutionSummary({
  execution,
}: Readonly<{ execution: NodeExecutionView }>) {
  return (
    <section className="panel-muted space-y-3 p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">当前节点</h3>
        <p className="text-sm leading-6 text-text-secondary">
          当前节点的提示词回放。
        </p>
      </header>
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
          <p>重试：{execution.retry_count}</p>
        </div>
      </div>
      {execution.error_message ? (
        <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm leading-6 text-accent-danger">
          {execution.error_message}
        </div>
      ) : null}
    </section>
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
    <section className="space-y-3">
      {replays.map((replay, index) => (
        <ReplayCard key={replay.id} replay={replay} index={index} />
      ))}
    </section>
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
    <article className="rounded-2xl bg-muted shadow-sm p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status="active" label={`#${index + 1}`} />
            <StatusBadge status="draft" label={formatReplayTypeLabel(replay.replay_type)} />
          </div>
          <div>
            <p className="text-sm font-medium text-text-primary">{replay.model_name}</p>
            <p className="text-sm leading-6 text-text-secondary">
              {formatReplayTokenUsage(replay)} · {formatDateTime(replay.created_at)}
            </p>
          </div>
        </div>
        <p className="text-sm leading-6 text-text-secondary">
          回放 ID：{formatShortId(replay.id)}
        </p>
      </div>
      <ReplayTextDisclosure title="提示词" value={replay.prompt_text} defaultOpen />
      <ReplayTextDisclosure title="响应" value={replay.response_text ?? "模型未返回文本响应。"} />
    </article>
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
      className="mt-4 rounded-2xl bg-muted shadow-sm"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-text-primary">
        {title}
      </summary>
      <div className="border-t border-line-soft px-4 py-4">
        <pre className="mono-block whitespace-pre-wrap break-words">{value}</pre>
      </div>
    </details>
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
      <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
        {message}
      </div>
    );
  }
  return <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{message}</div>;
}
