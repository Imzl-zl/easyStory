import assert from "node:assert/strict";
import test from "node:test";

import type { NodeExecutionView, ProjectPreparationStatus } from "@/lib/api/types";
import {
  buildEnginePathWithParams,
  createWorkflowBoundValue,
  resolveExecutionParamForWorkflow,
  resolveReplayExecutionSelection,
  resolveStartWorkflowDisabledReason,
  resolveWorkflowBoundValue,
  shouldRememberWorkflow,
  shouldResetSelectedExecution,
} from "./engine-page-support";

test("buildEnginePathWithParams updates and removes query params without leaving trailing question mark", () => {
  assert.equal(
    buildEnginePathWithParams("/workspace/project/p1/engine", "tab=replays&export=1", {
      export: null,
      execution: "exec-2",
      workflow: "wf-1",
    }),
    "/workspace/project/p1/engine?tab=replays&execution=exec-2&workflow=wf-1",
  );
  assert.equal(
    buildEnginePathWithParams("/workspace/project/p1/engine", "workflow=wf-1", {
      workflow: null,
    }),
    "/workspace/project/p1/engine",
  );
});

test("resolveReplayExecutionSelection only validates execution id after observability data is ready", () => {
  assert.deepEqual(
    resolveReplayExecutionSelection({
      canValidateSelection: false,
      executions: [],
      selectedExecutionId: "node-1",
    }),
    {
      activeSelectedExecutionId: "",
      shouldClearExecutionParam: false,
    },
  );
  assert.deepEqual(
    resolveReplayExecutionSelection({
      canValidateSelection: true,
      executions: [createExecution("node-1"), createExecution("node-2")],
      selectedExecutionId: "node-1",
    }),
    {
      activeSelectedExecutionId: "node-1",
      shouldClearExecutionParam: false,
    },
  );
  assert.deepEqual(
    resolveReplayExecutionSelection({
      canValidateSelection: true,
      executions: [createExecution("node-1"), createExecution("node-2")],
      selectedExecutionId: "node-9",
    }),
    {
      activeSelectedExecutionId: "",
      shouldClearExecutionParam: true,
    },
  );
});

test("resolveExecutionParamForWorkflow preserves execution only for the same workflow", () => {
  assert.equal(
    resolveExecutionParamForWorkflow({
      currentExecutionId: "exec-1",
      currentWorkflowId: "wf-1",
      nextWorkflowId: "wf-1",
    }),
    "exec-1",
  );
  assert.equal(
    resolveExecutionParamForWorkflow({
      currentExecutionId: "exec-1",
      currentWorkflowId: "wf-1",
      nextWorkflowId: "wf-2",
    }),
    null,
  );
  assert.equal(
    resolveExecutionParamForWorkflow({
      currentExecutionId: "",
      currentWorkflowId: "wf-1",
      nextWorkflowId: "wf-1",
    }),
    null,
  );
});

test("resolveWorkflowBoundValue only reuses local state for the active workflow", () => {
  assert.equal(
    resolveWorkflowBoundValue(createWorkflowBoundValue("wf-1", "node-1"), "wf-1", ""),
    "node-1",
  );
  assert.equal(
    resolveWorkflowBoundValue(createWorkflowBoundValue("wf-1", "node-1"), "wf-2", ""),
    "",
  );
});

test("shouldRememberWorkflow only persists a resolved workflow that differs from current memory", () => {
  assert.equal(
    shouldRememberWorkflow({
      hasWorkflow: true,
      rememberedWorkflowId: "wf-0",
      workflowId: "wf-1",
    }),
    true,
  );
  assert.equal(
    shouldRememberWorkflow({
      hasWorkflow: false,
      rememberedWorkflowId: "wf-0",
      workflowId: "wf-1",
    }),
    false,
  );
  assert.equal(
    shouldRememberWorkflow({
      hasWorkflow: true,
      rememberedWorkflowId: "wf-1",
      workflowId: "wf-1",
    }),
    false,
  );
});

test("shouldResetSelectedExecution clears stale selections only when current executions no longer contain it", () => {
  assert.equal(
    shouldResetSelectedExecution({
      executions: [createExecution("node-1"), createExecution("node-2")],
      selectedExecutionId: "node-9",
    }),
    true,
  );
  assert.equal(
    shouldResetSelectedExecution({
      executions: [createExecution("node-1"), createExecution("node-2")],
      selectedExecutionId: "node-1",
    }),
    false,
  );
  assert.equal(
    shouldResetSelectedExecution({
      executions: [],
      selectedExecutionId: "node-9",
    }),
    true,
  );
  assert.equal(
    shouldResetSelectedExecution({
      executions: [],
      selectedExecutionId: "",
    }),
    false,
  );
});

test("resolveStartWorkflowDisabledReason blocks start until preparation is ready", () => {
  assert.equal(
    resolveStartWorkflowDisabledReason({
      action: "pause",
      errorMessage: null,
      isLoading: false,
      preparation: undefined,
    }),
    null,
  );
  assert.equal(
    resolveStartWorkflowDisabledReason({
      action: "start",
      errorMessage: null,
      isLoading: true,
      preparation: undefined,
    }),
    "正在检查项目设定与前置资产状态。",
  );
  assert.equal(
    resolveStartWorkflowDisabledReason({
      action: "start",
      errorMessage: "准备状态加载失败",
      isLoading: false,
      preparation: undefined,
    }),
    "准备状态加载失败",
  );
  assert.equal(
    resolveStartWorkflowDisabledReason({
      action: "start",
      errorMessage: null,
      isLoading: false,
      preparation: createPreparationStatus({
        can_start_workflow: false,
        next_step_detail: "开篇设计必须先确认后才能启动工作流",
      }),
    }),
    "开篇设计必须先确认后才能启动工作流",
  );
  assert.equal(
    resolveStartWorkflowDisabledReason({
      action: "start",
      errorMessage: null,
      isLoading: false,
      preparation: createPreparationStatus({
        can_start_workflow: true,
        next_step_detail: "前置资产已就绪，可以启动工作流",
      }),
    }),
    null,
  );
});

function createExecution(id: string): NodeExecutionView {
  return {
    id,
    workflow_execution_id: "workflow-1",
    node_id: "generate",
    sequence: 1,
    node_order: 1,
    node_type: "generate",
    status: "running",
    input_summary: {},
    context_report: null,
    output_data: null,
    retry_count: 0,
    error_message: null,
    execution_time_ms: null,
    started_at: null,
    completed_at: null,
    artifacts: [],
    review_actions: [],
  };
}

function createPreparationStatus(
  overrides: Partial<ProjectPreparationStatus>,
): ProjectPreparationStatus {
  return {
    active_workflow: null,
    can_start_workflow: false,
    chapter_tasks: {
      counts: {
        completed: 0,
        failed: 0,
        generating: 0,
        interrupted: 0,
        pending: 0,
        skipped: 0,
        stale: 0,
      },
      step_status: "not_started",
      total: 0,
      workflow_execution_id: null,
    },
    next_step: "setting",
    next_step_detail: "请先补齐项目设定。",
    opening_plan: {
      content_id: null,
      content_status: null,
      has_content: false,
      step_status: "not_started",
      updated_at: null,
      version_number: null,
    },
    outline: {
      content_id: null,
      content_status: null,
      has_content: false,
      step_status: "not_started",
      updated_at: null,
      version_number: null,
    },
    project_id: "project-1",
    setting: {
      issues: [],
      status: "ready",
    },
    ...overrides,
  };
}
