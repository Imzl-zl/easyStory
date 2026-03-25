import assert from "node:assert/strict";
import test from "node:test";

import type { WorkflowExecution } from "@/lib/api/types";

import {
  buildWorkflowSummary,
  formatWorkflowStatusLabel,
} from "./engine-workflow-summary-support";

test("buildWorkflowSummary returns paused summary with manual mode and resume node", () => {
  const summary = buildWorkflowSummary(
    createWorkflow({
      current_node_name: "review_consistency",
      has_runtime_snapshot: true,
      mode: "manual",
      pause_reason: "review_failed",
      resume_from_node: "rewrite_chapter",
      status: "paused",
    }),
  );

  assert.deepEqual(summary, {
    description: "当前停在 review_consistency，恢复后将从 rewrite_chapter 继续。",
    modeLabel: "手动推进",
    modeTone: "draft",
    rows: [
      { label: "当前节点", value: "review_consistency" },
      { label: "恢复起点", value: "rewrite_chapter" },
      { label: "启动时间", value: "暂无" },
      { label: "完成时间", value: "暂无" },
    ],
    runtimeSnapshotLabel: "已记录快照",
    runtimeSnapshotTone: "active",
    statusLabel: "已暂停",
    statusTone: "paused",
    workflowIdentity: "主工作流 · v1",
  });
});

test("buildWorkflowSummary falls back to workflow id and safe empty-state labels", () => {
  const summary = buildWorkflowSummary(
    createWorkflow({
      current_node_id: null,
      current_node_name: null,
      has_runtime_snapshot: false,
      mode: null,
      status: "created",
      workflow_id: "draft-flow",
      workflow_name: null,
      workflow_version: null,
    }),
  );

  assert.deepEqual(summary, {
    description: "工作流已创建，等待启动。",
    modeLabel: "模式未声明",
    modeTone: "draft",
    rows: [
      { label: "当前节点", value: "尚未进入节点" },
      { label: "恢复起点", value: "无" },
      { label: "启动时间", value: "暂无" },
      { label: "完成时间", value: "暂无" },
    ],
    runtimeSnapshotLabel: "未记录快照",
    runtimeSnapshotTone: "draft",
    statusLabel: "待启动",
    statusTone: "created",
    workflowIdentity: "draft-flow",
  });
});

test("buildWorkflowSummary formats running workflow timestamps with shared formatter", () => {
  const summary = buildWorkflowSummary(
    createWorkflow({
      completed_at: "2026-03-25T07:00:00Z",
      current_node_id: "generate_chapter",
      current_node_name: null,
      mode: "auto",
      started_at: "2026-03-25T06:08:00Z",
      status: "running",
    }),
  );

  assert.equal(summary?.description, "当前正在执行 generate_chapter。");
  assert.equal(summary?.modeLabel, "自动推进");
  assert.equal(summary?.statusLabel, "运行中");
  assert.match(findSummaryRow(summary, "启动时间"), /^\d{2}\/\d{2} \d{2}:\d{2} UTC$/);
  assert.match(findSummaryRow(summary, "完成时间"), /^\d{2}\/\d{2} \d{2}:\d{2} UTC$/);
});

test("formatWorkflowStatusLabel keeps engine header status badge readable", () => {
  assert.equal(formatWorkflowStatusLabel("completed"), "已完成");
  assert.equal(formatWorkflowStatusLabel("failed"), "失败");
});

function createWorkflow(overrides: Partial<WorkflowExecution>): WorkflowExecution {
  return {
    execution_id: "workflow-1",
    project_id: "project-1",
    template_id: null,
    workflow_id: "workflow-template",
    workflow_name: "主工作流",
    workflow_version: "v1",
    mode: "manual",
    status: "created",
    current_node_id: null,
    current_node_name: null,
    pause_reason: null,
    resume_from_node: null,
    has_runtime_snapshot: false,
    started_at: null,
    completed_at: null,
    nodes: [],
    ...overrides,
  };
}

function findSummaryRow(
  summary: ReturnType<typeof buildWorkflowSummary>,
  label: string,
): string {
  const row = summary?.rows.find((item) => item.label === label);
  assert.ok(row);
  return row.value;
}
