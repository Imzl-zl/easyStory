import assert from "node:assert/strict";
import test from "node:test";

import type { WorkflowExecution } from "@/lib/api/types";

import { resolveWorkflowStatusCallout } from "./engine-workflow-status-support";

test("resolveWorkflowStatusCallout returns review jump when workflow paused by review failure", () => {
  const result = resolveWorkflowStatusCallout(
    createWorkflow({
      current_node_name: "review consistency",
      pause_reason: "review_failed",
      resume_from_node: "rewrite_chapter",
      status: "paused",
    }),
  );

  assert.deepEqual(result, {
    actionLabel: "查看审核",
    description:
      "当前工作流因审核未通过而暂停，需先处理 reviewer 问题。 当前停在 review consistency。 恢复后将从 rewrite_chapter 继续。",
    targetTab: "reviews",
    title: "审核未通过",
    tone: "warning",
  });
});

test("resolveWorkflowStatusCallout routes budget pause to billing and runtime error to danger overview", () => {
  assert.deepEqual(
    resolveWorkflowStatusCallout(
      createWorkflow({
        pause_reason: "budget_exceeded",
        status: "paused",
      }),
    ),
    {
      actionLabel: "查看预算",
      description: "当前工作流因预算超限而暂停，需先检查 token 与成本口径。",
      targetTab: "billing",
      title: "预算触发暂停",
      tone: "warning",
    },
  );

  assert.deepEqual(
    resolveWorkflowStatusCallout(
      createWorkflow({
        pause_reason: "error",
        status: "paused",
      }),
    ),
    {
      actionLabel: "查看概览",
      description: "当前工作流因运行时错误而暂停。",
      targetTab: "overview",
      title: "运行时错误暂停",
      tone: "danger",
    },
  );
});

test("resolveWorkflowStatusCallout returns null unless workflow is paused with a reason", () => {
  assert.equal(resolveWorkflowStatusCallout(null), null);
  assert.equal(
    resolveWorkflowStatusCallout(
      createWorkflow({
        pause_reason: "review_failed",
        status: "running",
      }),
    ),
    null,
  );
  assert.equal(
    resolveWorkflowStatusCallout(
      createWorkflow({
        pause_reason: null,
        status: "paused",
      }),
    ),
    null,
  );
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
