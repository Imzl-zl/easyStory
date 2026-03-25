import type { WorkflowExecution } from "@/lib/api/types";

import { formatDateTime, formatShortId } from "./engine-logs-format";

export type WorkflowSummaryRow = {
  label: string;
  value: string;
};

export type WorkflowSummaryCardData = {
  description: string;
  modeLabel: string;
  modeTone: "active" | "draft";
  rows: WorkflowSummaryRow[];
  runtimeSnapshotLabel: string;
  runtimeSnapshotTone: "active" | "draft";
  statusLabel: string;
  statusTone: WorkflowExecution["status"];
  workflowIdentity: string;
};

const WORKFLOW_STATUS_LABELS: Record<WorkflowExecution["status"], string> = {
  created: "待启动",
  running: "运行中",
  paused: "已暂停",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export function buildWorkflowSummary(
  workflow: WorkflowExecution | null | undefined,
): WorkflowSummaryCardData | null {
  if (!workflow) {
    return null;
  }
  return {
    description: buildWorkflowDescription(workflow),
    modeLabel: formatWorkflowModeLabel(workflow.mode),
    modeTone: resolveWorkflowModeTone(workflow.mode),
    rows: [
      { label: "当前节点", value: resolveCurrentNodeLabel(workflow) },
      { label: "恢复起点", value: workflow.resume_from_node ?? "无" },
      { label: "启动时间", value: formatDateTime(workflow.started_at) },
      { label: "完成时间", value: formatDateTime(workflow.completed_at) },
    ],
    runtimeSnapshotLabel: resolveRuntimeSnapshotLabel(workflow.has_runtime_snapshot),
    runtimeSnapshotTone: workflow.has_runtime_snapshot ? "active" : "draft",
    statusLabel: formatWorkflowStatusLabel(workflow.status),
    statusTone: workflow.status,
    workflowIdentity: buildWorkflowIdentity(workflow),
  };
}

export function formatWorkflowStatusLabel(
  status: WorkflowExecution["status"],
): string {
  return WORKFLOW_STATUS_LABELS[status];
}

export function resolveWorkflowCurrentNodeLabel(
  workflow: WorkflowExecution,
): string {
  const currentNode = workflow.current_node_name ?? workflow.current_node_id;
  if (currentNode) {
    return currentNode;
  }
  switch (workflow.status) {
    case "created":
      return "尚未进入节点";
    case "completed":
      return "本次执行已完成";
    case "cancelled":
      return "本次执行已取消";
    default:
      return "暂未上报";
  }
}

function formatWorkflowModeLabel(
  mode: WorkflowExecution["mode"],
): string {
  if (mode === "auto") {
    return "自动推进";
  }
  if (mode === "manual") {
    return "手动推进";
  }
  return "模式未声明";
}

function resolveWorkflowModeTone(
  mode: WorkflowExecution["mode"],
): "active" | "draft" {
  return mode === "auto" ? "active" : "draft";
}

function resolveRuntimeSnapshotLabel(hasRuntimeSnapshot: boolean): string {
  return hasRuntimeSnapshot ? "已记录快照" : "未记录快照";
}

function buildWorkflowIdentity(workflow: WorkflowExecution): string {
  const primary =
    workflow.workflow_name ??
    workflow.workflow_id ??
    `执行批次 ${formatShortId(workflow.execution_id)}`;
  if (!workflow.workflow_version) {
    return primary;
  }
  return `${primary} · ${workflow.workflow_version}`;
}

function resolveCurrentNodeLabel(workflow: WorkflowExecution): string {
  return resolveWorkflowCurrentNodeLabel(workflow);
}

function buildWorkflowDescription(workflow: WorkflowExecution): string {
  const currentNode = workflow.current_node_name ?? workflow.current_node_id;
  if (workflow.status === "created") {
    return currentNode
      ? `工作流已创建，首个节点为 ${currentNode}。`
      : "工作流已创建，等待启动。";
  }
  if (workflow.status === "running") {
    return currentNode ? `当前正在执行 ${currentNode}。` : "当前工作流正在推进。";
  }
  if (workflow.status === "paused") {
    if (currentNode && workflow.resume_from_node) {
      return `当前停在 ${currentNode}，恢复后将从 ${workflow.resume_from_node} 继续。`;
    }
    return currentNode
      ? `当前停在 ${currentNode}，等待恢复或处理阻塞。`
      : "当前工作流已暂停，等待恢复或处理阻塞。";
  }
  if (workflow.status === "completed") {
    return currentNode ? `本次执行已在 ${currentNode} 完成。` : "本次执行已完成。";
  }
  if (workflow.status === "failed") {
    return currentNode
      ? `本次执行在 ${currentNode} 失败，请先检查日志与上下游状态。`
      : "本次执行失败，请先检查日志与上下游状态。";
  }
  return "本次执行已取消，不会继续推进。";
}
