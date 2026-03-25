import assert from "node:assert/strict";
import test from "node:test";

import type { NodeExecutionView } from "@/lib/api/types";
import {
  buildEnginePathWithParams,
  createWorkflowBoundValue,
  resolveWorkflowBoundValue,
  shouldRememberWorkflow,
  shouldResetSelectedExecution,
} from "./engine-page-support";

test("buildEnginePathWithParams updates and removes query params without leaving trailing question mark", () => {
  assert.equal(
    buildEnginePathWithParams("/workspace/project/p1/engine", "tab=replays&export=1", {
      export: null,
      workflow: "wf-1",
    }),
    "/workspace/project/p1/engine?tab=replays&workflow=wf-1",
  );
  assert.equal(
    buildEnginePathWithParams("/workspace/project/p1/engine", "workflow=wf-1", {
      workflow: null,
    }),
    "/workspace/project/p1/engine",
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
