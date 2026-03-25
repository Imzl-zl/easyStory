import type {
  ExecutionLogView,
  NodeExecutionStatus,
  NodeExecutionView,
} from "@/lib/api/types";

const ACTIVE_EXECUTION_STATUSES = new Set<NodeExecutionStatus>([
  "running",
  "running_stream",
  "reviewing",
  "fixing",
]);

export type EngineLogsSummary = {
  activeExecutionCount: number;
  artifactCount: number;
  failedExecutionCount: number;
  latestActivityAt: string | null;
  orderedExecutions: NodeExecutionView[];
  orderedLogs: ExecutionLogView[];
  reviewCount: number;
};

export function buildEngineLogsSummary(
  executions: NodeExecutionView[],
  logs: ExecutionLogView[],
): EngineLogsSummary {
  return {
    activeExecutionCount: executions.filter((execution) =>
      ACTIVE_EXECUTION_STATUSES.has(execution.status),
    ).length,
    artifactCount: executions.reduce(
      (total, item) => total + item.artifacts.length,
      0,
    ),
    failedExecutionCount: executions.filter(
      (execution) => execution.status === "failed",
    ).length,
    latestActivityAt: resolveLatestActivity(executions, logs),
    orderedExecutions: [...executions].sort(compareExecutions),
    orderedLogs: [...logs].sort(compareLogs),
    reviewCount: executions.reduce(
      (total, item) => total + item.review_actions.length,
      0,
    ),
  };
}

export function formatDetailValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value) ?? "undefined";
}

function compareExecutions(
  left: NodeExecutionView,
  right: NodeExecutionView,
): number {
  const leftTime = new Date(left.completed_at ?? left.started_at ?? 0).getTime();
  const rightTime = new Date(
    right.completed_at ?? right.started_at ?? 0,
  ).getTime();
  return (
    rightTime - leftTime ||
    right.node_order - left.node_order ||
    right.sequence - left.sequence
  );
}

function compareLogs(left: ExecutionLogView, right: ExecutionLogView): number {
  return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
}

function resolveLatestActivity(
  executions: NodeExecutionView[],
  logs: ExecutionLogView[],
): string | null {
  const executionTimes = executions
    .map((execution) => execution.completed_at ?? execution.started_at)
    .filter((value): value is string => value !== null);
  const logTimes = logs.map((log) => log.created_at);
  const latest = [...executionTimes, ...logTimes].sort(
    (left, right) => new Date(right).getTime() - new Date(left).getTime(),
  )[0];
  return latest ?? null;
}
