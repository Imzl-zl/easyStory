import type {
  NodeExecutionStatus,
  NodeExecutionView,
  WorkflowExecution,
  WorkflowNodeSummary,
} from "@/lib/api/types";

import {
  formatCount,
  formatDateTime,
  formatDuration,
  formatExecutionStatusLabel,
  resolveExecutionTone,
} from "./engine-logs-format";
import {
  formatWorkflowStatusLabel,
  resolveWorkflowCurrentNodeLabel,
} from "./engine-workflow-summary-support";

type TimelineTone = "draft" | "active" | "completed" | "warning" | "failed" | "stale";

export type EngineOverviewMetric = {
  detail: string;
  label: string;
  value: string;
};

export type EngineOverviewTimelineBadge = {
  label: string;
  status: "active" | "warning";
};

export type EngineOverviewTimelineItem = {
  badges: EngineOverviewTimelineBadge[];
  detail: string;
  errorMessage: string | null;
  isRuntimeOnly: boolean;
  key: string;
  latestExecutionId: string | null;
  statusKey: NodeExecutionStatus | "waiting";
  statusLabel: string;
  statusTone: TimelineTone;
  subtitle: string;
  timeDetail: string;
  title: string;
};

const ACTIVE_TIMELINE_STATUSES = new Set<NodeExecutionStatus>([
  "running",
  "running_stream",
  "reviewing",
  "fixing",
]);

const COMPLETED_TIMELINE_STATUSES = new Set<NodeExecutionStatus>([
  "completed",
  "skipped",
]);

export type EngineOverviewData = {
  metrics: EngineOverviewMetric[];
  timeline: EngineOverviewTimelineItem[];
};

export function buildEngineOverview(
  workflow: WorkflowExecution | null | undefined,
  executions: NodeExecutionView[],
): EngineOverviewData | null {
  if (!workflow) {
    return null;
  }
  const timeline = buildOverviewTimeline(workflow, executions);
  return {
    metrics: buildOverviewMetrics(workflow, executions, timeline),
    timeline,
  };
}

function buildOverviewMetrics(
  workflow: WorkflowExecution,
  executions: NodeExecutionView[],
  timeline: EngineOverviewTimelineItem[],
): EngineOverviewMetric[] {
  const workflowTimeline = timeline.filter((item) => !item.isRuntimeOnly);
  const activeCount = workflowTimeline.filter((item) => isActiveTimelineStatus(item.statusKey)).length;
  const completedCount = workflowTimeline.filter((item) =>
    isCompletedTimelineStatus(item.statusKey),
  ).length;
  const failedCount = workflowTimeline.filter((item) => item.statusKey === "failed").length;
  const artifacts = executions.reduce((total, item) => total + item.artifacts.length, 0);
  const reviews = executions.reduce((total, item) => total + item.review_actions.length, 0);
  return [
    {
      detail: `进行中 ${formatCount(activeCount)}，失败 ${formatCount(failedCount)}`,
      label: "节点推进",
      value: `${formatCount(completedCount)}/${formatCount(workflow.nodes.length)}`,
    },
    {
      detail: `Workflow ${formatWorkflowStatusLabel(workflow.status)}`,
      label: "当前焦点",
      value: resolveWorkflowCurrentNodeLabel(workflow),
    },
    {
      detail: "按 workflow 与 node execution 时间共同判断",
      label: "最新活动",
      value: formatDateTime(resolveLatestActivity(workflow, executions)),
    },
    {
      detail: `产物 ${formatCount(artifacts)}，审查 ${formatCount(reviews)}`,
      label: "执行记录",
      value: formatCount(executions.length),
    },
  ];
}

function buildOverviewTimeline(
  workflow: WorkflowExecution,
  executions: NodeExecutionView[],
): EngineOverviewTimelineItem[] {
  const grouped = groupExecutionsByNode(executions);
  const knownNodeIds = new Set(workflow.nodes.map((node) => node.id));
  const workflowTimeline = workflow.nodes.map((node) =>
    buildWorkflowTimelineItem(node, grouped.get(node.id) ?? [], workflow),
  );
  const runtimeOnlyTimeline = Array.from(grouped.entries())
    .filter(([nodeId]) => !knownNodeIds.has(nodeId))
    .sort((left, right) => compareExecutions(left[1][0], right[1][0]))
    .map(([, items]) => buildRuntimeOnlyTimelineItem(items, workflow));
  return [...workflowTimeline, ...runtimeOnlyTimeline];
}

function buildWorkflowTimelineItem(
  node: WorkflowNodeSummary,
  executions: NodeExecutionView[],
  workflow: WorkflowExecution,
): EngineOverviewTimelineItem {
  const latest = executions[0] ?? null;
  if (!latest) {
    return {
      badges: buildTimelineBadges(node.id, workflow, false),
      detail: buildWaitingDetail(node),
      errorMessage: null,
      isRuntimeOnly: false,
      key: node.id,
      latestExecutionId: null,
      statusKey: "waiting",
      statusLabel: "等待执行",
      statusTone: "draft",
      subtitle: `${node.id} · ${node.node_type}`,
      timeDetail: "尚无执行记录",
      title: node.name,
    };
  }
  return {
    badges: buildTimelineBadges(node.id, workflow, false),
    detail: buildExecutionDetail(latest, executions.length, false),
    errorMessage: latest.error_message,
    isRuntimeOnly: false,
    key: node.id,
    latestExecutionId: latest.id,
    statusKey: latest.status,
    statusLabel: formatExecutionStatusLabel(latest.status),
    statusTone: resolveExecutionTone(latest.status),
    subtitle: `${node.id} · ${node.node_type}`,
    timeDetail: buildExecutionTimeDetail(latest),
    title: node.name,
  };
}

function buildRuntimeOnlyTimelineItem(
  executions: NodeExecutionView[],
  workflow: WorkflowExecution,
): EngineOverviewTimelineItem {
  const latest = executions[0];
  return {
    badges: buildTimelineBadges(latest.node_id, workflow, true),
    detail: buildExecutionDetail(latest, executions.length, true),
    errorMessage: latest.error_message,
    isRuntimeOnly: true,
    key: `runtime-only-${latest.node_id}`,
    latestExecutionId: latest.id,
    statusKey: latest.status,
    statusLabel: formatExecutionStatusLabel(latest.status),
    statusTone: resolveExecutionTone(latest.status),
    subtitle: `${latest.node_id} · ${latest.node_type}`,
    timeDetail: buildExecutionTimeDetail(latest),
    title: latest.node_id,
  };
}

function groupExecutionsByNode(
  executions: NodeExecutionView[],
): Map<string, NodeExecutionView[]> {
  const grouped = new Map<string, NodeExecutionView[]>();
  const ordered = [...executions].sort(compareExecutions);
  for (const execution of ordered) {
    const items = grouped.get(execution.node_id) ?? [];
    items.push(execution);
    grouped.set(execution.node_id, items);
  }
  return grouped;
}

function buildTimelineBadges(
  nodeId: string,
  workflow: WorkflowExecution,
  isRuntimeOnly: boolean,
): EngineOverviewTimelineBadge[] {
  const badges: EngineOverviewTimelineBadge[] = [];
  if (workflow.current_node_id === nodeId) {
    badges.push({ label: "当前节点", status: "active" });
  }
  if (workflow.resume_from_node === nodeId) {
    badges.push({ label: "恢复起点", status: "warning" });
  }
  if (isRuntimeOnly) {
    badges.push({ label: "定义外节点", status: "warning" });
  }
  return badges;
}

function buildWaitingDetail(node: WorkflowNodeSummary): string {
  if (node.depends_on.length === 0) {
    return "无上游依赖，工作流启动后即可进入执行。";
  }
  return `依赖 ${node.depends_on.join("、")} 完成后才会进入执行。`;
}

function buildExecutionDetail(
  execution: NodeExecutionView,
  count: number,
  isRuntimeOnly: boolean,
): string {
  const detail =
    `执行 ${formatCount(count)} 次 · 重试 ${formatCount(execution.retry_count)} 次 · ` +
    `产物 ${formatCount(execution.artifacts.length)} · 审查 ${formatCount(execution.review_actions.length)}`;
  if (!isRuntimeOnly) {
    return detail;
  }
  return `${detail} · 该节点存在 runtime 记录，但未出现在 workflow 定义中。`;
}

function buildExecutionTimeDetail(execution: NodeExecutionView): string {
  return `开始 ${formatDateTime(execution.started_at)} · 完成 ${formatDateTime(execution.completed_at)} · 耗时 ${formatDuration(execution.execution_time_ms)}`;
}

function resolveLatestActivity(
  workflow: WorkflowExecution,
  executions: NodeExecutionView[],
): string | null {
  const workflowTimes = [workflow.started_at, workflow.completed_at];
  const executionTimes = executions.flatMap((item) => [item.started_at, item.completed_at]);
  const values = [...workflowTimes, ...executionTimes].filter(
    (value): value is string => value !== null,
  );
  const latest = values.sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0];
  return latest ?? null;
}

function compareExecutions(
  left: NodeExecutionView,
  right: NodeExecutionView,
): number {
  const leftTime = new Date(left.completed_at ?? left.started_at ?? 0).getTime();
  const rightTime = new Date(right.completed_at ?? right.started_at ?? 0).getTime();
  return rightTime - leftTime || right.node_order - left.node_order || right.sequence - left.sequence;
}

function isActiveTimelineStatus(
  status: EngineOverviewTimelineItem["statusKey"],
): status is NodeExecutionStatus {
  return status !== "waiting" && ACTIVE_TIMELINE_STATUSES.has(status);
}

function isCompletedTimelineStatus(
  status: EngineOverviewTimelineItem["statusKey"],
): status is NodeExecutionStatus {
  return status !== "waiting" && COMPLETED_TIMELINE_STATUSES.has(status);
}
