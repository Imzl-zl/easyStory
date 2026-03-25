import type { NodeExecutionView, PromptReplayView } from "@/lib/api/types";

import {
  formatExecutionStatusLabel,
  formatShortId,
} from "./engine-logs-format";

const REPLAY_TYPE_LABELS: Record<string, string> = {
  fix: "精修回放",
  generate: "生成回放",
};

const NUMBER_FORMATTER = new Intl.NumberFormat("zh-CN");

export type ReplayGateState =
  | "workflow-empty"
  | "executions-error"
  | "executions-loading"
  | "executions-empty"
  | "ready";

export type ReplayDetailState =
  | "selection-required"
  | "replays-error"
  | "replays-loading"
  | "replays-empty"
  | "ready";

export function resolveReplayGateState({
  executionCount,
  executionsErrorMessage,
  isExecutionsLoading,
  isWorkflowReady,
}: {
  executionCount: number;
  executionsErrorMessage: string | null;
  isExecutionsLoading: boolean;
  isWorkflowReady: boolean;
}): ReplayGateState {
  if (!isWorkflowReady) {
    return "workflow-empty";
  }
  if (isExecutionsLoading && executionCount === 0) {
    return "executions-loading";
  }
  if (executionCount === 0) {
    if (executionsErrorMessage) {
      return "executions-error";
    }
    return "executions-empty";
  }
  return "ready";
}

export function resolveReplayDetailState({
  replayCount,
  replaysErrorMessage,
  selectedExecutionId,
  isReplaysLoading,
}: {
  replayCount: number;
  replaysErrorMessage: string | null;
  selectedExecutionId: string;
  isReplaysLoading: boolean;
}): ReplayDetailState {
  if (!selectedExecutionId) {
    return "selection-required";
  }
  if (isReplaysLoading && replayCount === 0) {
    return "replays-loading";
  }
  if (replayCount === 0) {
    if (replaysErrorMessage) {
      return "replays-error";
    }
    return "replays-empty";
  }
  return "ready";
}

export function formatReplayExecutionOptionLabel(
  execution: NodeExecutionView,
): string {
  return `${execution.node_id} · 序列 ${execution.sequence} · ${formatExecutionStatusLabel(execution.status)} · ${formatShortId(execution.id)}`;
}

export function formatReplayTypeLabel(value: string): string {
  return REPLAY_TYPE_LABELS[value] ?? value.replaceAll("_", " ");
}

export function formatReplayTokenUsage(replay: PromptReplayView): string {
  const inputText = formatTokenValue(replay.input_tokens);
  const outputText = formatTokenValue(replay.output_tokens);
  return `${inputText} 输入 / ${outputText} 输出`;
}

export function sortPromptReplays(replays: PromptReplayView[]): PromptReplayView[] {
  return [...replays].sort(comparePromptReplayByTime);
}

function comparePromptReplayByTime(
  left: PromptReplayView,
  right: PromptReplayView,
): number {
  return new Date(left.created_at).getTime() - new Date(right.created_at).getTime();
}

function formatTokenValue(value: number | null): string {
  if (value === null) {
    return "未记录";
  }
  return NUMBER_FORMATTER.format(value);
}
