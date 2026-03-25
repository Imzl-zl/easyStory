import assert from "node:assert/strict";
import test from "node:test";

import type {
  ExecutionLogView,
  NodeExecutionStatus,
  NodeExecutionView,
} from "@/lib/api/types";

import {
  buildEngineLogsSummary,
  formatDetailValue,
} from "./engine-logs-panel-support";

test("buildEngineLogsSummary aggregates counts and sorts executions/logs by latest activity", () => {
  const summary = buildEngineLogsSummary(
    [
      createExecution({
        artifacts: [createArtifact()],
        completed_at: "2026-03-25T07:05:00Z",
        id: "execution-older",
        sequence: 1,
        started_at: "2026-03-25T07:00:00Z",
        status: "failed",
      }),
      createExecution({
        id: "execution-newer",
        review_actions: [createReview()],
        sequence: 2,
        started_at: "2026-03-25T07:08:00Z",
        status: "reviewing",
      }),
    ],
    [
      createLog({
        created_at: "2026-03-25T07:03:00Z",
        id: "log-older",
      }),
      createLog({
        created_at: "2026-03-25T07:10:00Z",
        id: "log-newer",
      }),
    ],
  );

  assert.equal(summary.failedExecutionCount, 1);
  assert.equal(summary.activeExecutionCount, 1);
  assert.equal(summary.artifactCount, 1);
  assert.equal(summary.reviewCount, 1);
  assert.equal(summary.latestActivityAt, "2026-03-25T07:10:00Z");
  assert.deepEqual(
    summary.orderedExecutions.map((execution) => execution.id),
    ["execution-newer", "execution-older"],
  );
  assert.deepEqual(
    summary.orderedLogs.map((log) => log.id),
    ["log-newer", "log-older"],
  );
});

test("formatDetailValue keeps strings and stringifies structured values", () => {
  assert.equal(formatDetailValue("plain text"), "plain text");
  assert.equal(formatDetailValue(42), "42");
  assert.equal(formatDetailValue(false), "false");
  assert.equal(formatDetailValue({ branch: "chapter_generate" }), "{\"branch\":\"chapter_generate\"}");
  assert.equal(formatDetailValue(undefined), "undefined");
});

function createExecution(
  overrides: Partial<NodeExecutionView> & {
    status: NodeExecutionStatus;
  },
): NodeExecutionView {
  const { status, ...rest } = overrides;
  return {
    id: "execution-1",
    workflow_execution_id: "workflow-1",
    node_id: "chapter_generate",
    sequence: 1,
    node_order: 1,
    node_type: "generate",
    status,
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
    ...rest,
  };
}

function createLog(overrides: Partial<ExecutionLogView>): ExecutionLogView {
  return {
    id: "log-1",
    workflow_execution_id: "workflow-1",
    node_execution_id: "execution-1",
    level: "INFO",
    message: "Node started",
    details: null,
    created_at: "2026-03-25T07:00:00Z",
    ...overrides,
  };
}

function createArtifact() {
  return {
    id: "artifact-1",
    artifact_type: "chapter_draft",
    content_version_id: null,
    payload: null,
    word_count: 1200,
    created_at: "2026-03-25T07:05:00Z",
  };
}

function createReview() {
  return {
    id: "review-1",
    agent_id: "reviewer.main",
    reviewer_name: "Main Reviewer",
    review_type: "quality",
    status: "warning" as const,
    score: 0.85,
    summary: "Need another pass",
    issues: null,
    execution_time_ms: 800,
    tokens_used: 240,
    created_at: "2026-03-25T07:09:00Z",
  };
}
