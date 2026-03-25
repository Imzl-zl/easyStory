import assert from "node:assert/strict";
import test from "node:test";

import type {
  NodeExecutionStatus,
  NodeExecutionView,
  WorkflowExecution,
} from "@/lib/api/types";

import { buildEngineOverview } from "./engine-overview-support";

test("buildEngineOverview aggregates workflow metrics and ordered timeline from workflow nodes", () => {
  const overview = buildEngineOverview(
    createWorkflow({
      current_node_id: "review_consistency",
      current_node_name: "一致性审核",
      started_at: "2026-03-25T06:00:00Z",
      status: "running",
    }),
    [
      createExecution({
        artifacts: [createArtifact()],
        completed_at: "2026-03-25T06:20:00Z",
        node_id: "chapter_generate",
        node_order: 1,
        review_actions: [],
        sequence: 1,
        started_at: "2026-03-25T06:10:00Z",
        status: "completed",
      }),
      createExecution({
        node_id: "review_consistency",
        node_order: 2,
        review_actions: [createReview()],
        sequence: 1,
        started_at: "2026-03-25T06:21:00Z",
        status: "reviewing",
      }),
    ],
  );

  assert.ok(overview);
  assert.deepEqual(overview.metrics[0], {
    detail: "进行中 1，失败 0",
    label: "节点推进",
    value: "1/2",
  });
  assert.equal(overview.metrics[1].value, "一致性审核");
  assert.equal(overview.timeline.length, 2);
  assert.equal(overview.timeline[0].title, "章节生成");
  assert.equal(overview.timeline[0].statusLabel, "已完成");
  assert.equal(overview.timeline[0].latestExecutionId, "execution-1");
  assert.equal(overview.timeline[1].statusLabel, "审核中");
  assert.equal(overview.timeline[1].latestExecutionId, "execution-1");
  assert.deepEqual(overview.timeline[1].badges, [{ label: "当前节点", status: "active" }]);
});

test("buildEngineOverview keeps waiting nodes when runtime query succeeded with no executions", () => {
  const overview = buildEngineOverview(
    createWorkflow({
      current_node_id: null,
      current_node_name: null,
      status: "created",
    }),
    [],
  );

  assert.ok(overview);
  assert.deepEqual(overview.metrics[0], {
    detail: "进行中 0，失败 0",
    label: "节点推进",
    value: "0/2",
  });
  assert.equal(overview.timeline[0].statusLabel, "等待执行");
  assert.equal(overview.timeline[0].latestExecutionId, null);
  assert.equal(overview.timeline[0].timeDetail, "尚无执行记录");
  assert.match(overview.timeline[1].detail, /依赖 chapter_generate/);
});

test("buildEngineOverview appends runtime-only node records instead of dropping them", () => {
  const overview = buildEngineOverview(
    createWorkflow({
      resume_from_node: "patch_rewrite",
      status: "paused",
    }),
    [
      createExecution({
        error_message: "Schema validation failed",
        node_id: "patch_rewrite",
        node_order: 9,
        sequence: 2,
        status: "failed",
      }),
    ],
  );

  assert.ok(overview);
  assert.equal(overview.timeline.length, 3);
  const runtimeOnly = overview.timeline[2];
  assert.equal(runtimeOnly.isRuntimeOnly, true);
  assert.deepEqual(runtimeOnly.badges, [
    { label: "恢复起点", status: "warning" },
    { label: "定义外节点", status: "warning" },
  ]);
  assert.equal(runtimeOnly.latestExecutionId, "execution-1");
  assert.match(runtimeOnly.detail, /未出现在 workflow 定义中/);
  assert.equal(runtimeOnly.errorMessage, "Schema validation failed");
});

test("buildEngineOverview counts skipped node as completed progress", () => {
  const overview = buildEngineOverview(
    createWorkflow({
      status: "completed",
    }),
    [
      createExecution({
        completed_at: "2026-03-25T06:20:00Z",
        node_id: "chapter_generate",
        node_order: 1,
        sequence: 1,
        started_at: "2026-03-25T06:10:00Z",
        status: "skipped",
      }),
      createExecution({
        completed_at: "2026-03-25T06:30:00Z",
        node_id: "review_consistency",
        node_order: 2,
        sequence: 1,
        started_at: "2026-03-25T06:25:00Z",
        status: "completed",
      }),
    ],
  );

  assert.ok(overview);
  assert.deepEqual(overview.metrics[0], {
    detail: "进行中 0，失败 0",
    label: "节点推进",
    value: "2/2",
  });
  assert.equal(overview.timeline[0].statusLabel, "已跳过");
  assert.equal(overview.timeline[0].statusKey, "skipped");
});

test("buildEngineOverview returns null without workflow", () => {
  assert.equal(buildEngineOverview(null, []), null);
});

function createWorkflow(overrides: Partial<WorkflowExecution>): WorkflowExecution {
  return {
    execution_id: "workflow-1",
    project_id: "project-1",
    template_id: null,
    workflow_id: "story-main",
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
    nodes: [
      {
        depends_on: [],
        id: "chapter_generate",
        name: "章节生成",
        node_type: "generate",
      },
      {
        depends_on: ["chapter_generate"],
        id: "review_consistency",
        name: "一致性审核",
        node_type: "review",
      },
    ],
    ...overrides,
  };
}

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

function createArtifact() {
  return {
    id: "artifact-1",
    artifact_type: "chapter_draft",
    content_version_id: null,
    payload: null,
    word_count: 1200,
    created_at: "2026-03-25T06:20:00Z",
  };
}

function createReview() {
  return {
    id: "review-1",
    agent_id: "reviewer.main",
    reviewer_name: "Main Reviewer",
    review_type: "quality",
    status: "warning" as const,
    score: 0.8,
    summary: "Need polish",
    issues: null,
    execution_time_ms: 1200,
    tokens_used: 300,
    created_at: "2026-03-25T06:22:00Z",
  };
}
