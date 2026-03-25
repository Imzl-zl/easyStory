import assert from "node:assert/strict";
import test from "node:test";

import type { PromptReplayView } from "@/lib/api/types";
import {
  formatReplayExecutionOptionLabel,
  formatReplayTokenUsage,
  formatReplayTypeLabel,
  resolveReplayDetailState,
  resolveReplayGateState,
  sortPromptReplays,
} from "./engine-replay-support";
import type { NodeExecutionView } from "@/lib/api/types";

test("resolveReplayGateState follows workflow then error then loading then empty order", () => {
  assert.equal(
    resolveReplayGateState({
      executionCount: 0,
      executionsErrorMessage: null,
      isExecutionsLoading: false,
      isWorkflowReady: false,
    }),
    "workflow-empty",
  );
  assert.equal(
    resolveReplayGateState({
      executionCount: 2,
      executionsErrorMessage: "boom",
      isExecutionsLoading: false,
      isWorkflowReady: true,
    }),
    "ready",
  );
  assert.equal(
    resolveReplayGateState({
      executionCount: 0,
      executionsErrorMessage: "boom",
      isExecutionsLoading: false,
      isWorkflowReady: true,
    }),
    "executions-error",
  );
  assert.equal(
    resolveReplayGateState({
      executionCount: 0,
      executionsErrorMessage: null,
      isExecutionsLoading: true,
      isWorkflowReady: true,
    }),
    "executions-loading",
  );
  assert.equal(
    resolveReplayGateState({
      executionCount: 0,
      executionsErrorMessage: null,
      isExecutionsLoading: false,
      isWorkflowReady: true,
    }),
    "executions-empty",
  );
});

test("resolveReplayDetailState requires a selected execution before replay fetch states", () => {
  assert.equal(
    resolveReplayDetailState({
      replayCount: 0,
      replaysErrorMessage: "boom",
      selectedExecutionId: "",
      isReplaysLoading: true,
    }),
    "selection-required",
  );
  assert.equal(
    resolveReplayDetailState({
      replayCount: 1,
      replaysErrorMessage: "boom",
      selectedExecutionId: "exec-1",
      isReplaysLoading: false,
    }),
    "ready",
  );
  assert.equal(
    resolveReplayDetailState({
      replayCount: 0,
      replaysErrorMessage: "boom",
      selectedExecutionId: "exec-1",
      isReplaysLoading: false,
    }),
    "replays-error",
  );
  assert.equal(
    resolveReplayDetailState({
      replayCount: 0,
      replaysErrorMessage: null,
      selectedExecutionId: "exec-1",
      isReplaysLoading: true,
    }),
    "replays-loading",
  );
  assert.equal(
    resolveReplayDetailState({
      replayCount: 0,
      replaysErrorMessage: null,
      selectedExecutionId: "exec-1",
      isReplaysLoading: false,
    }),
    "replays-empty",
  );
  assert.equal(
    resolveReplayDetailState({
      replayCount: 1,
      replaysErrorMessage: null,
      selectedExecutionId: "exec-1",
      isReplaysLoading: false,
    }),
    "ready",
  );
});

test("format helpers expose replay type labels, token usage, and stable chronology", () => {
  assert.equal(formatReplayTypeLabel("generate"), "生成回放");
  assert.equal(formatReplayTypeLabel("post_review_fix"), "post review fix");
  assert.equal(
    formatReplayExecutionOptionLabel(createExecution({ id: "abcdef12-34", sequence: 3 })),
    "generate · 序列 3 · 执行中 · abcdef12",
  );
  assert.equal(
    formatReplayTokenUsage(createReplay({ input_tokens: 1200, output_tokens: 345 })),
    "1,200 输入 / 345 输出",
  );
  assert.deepEqual(
    sortPromptReplays([
      createReplay({ id: "later", created_at: "2026-03-25T12:00:00Z" }),
      createReplay({ id: "earlier", created_at: "2026-03-25T11:00:00Z" }),
    ]).map((item) => item.id),
    ["earlier", "later"],
  );
});

function createReplay(overrides: Partial<PromptReplayView>): PromptReplayView {
  return {
    id: "replay-1",
    node_execution_id: "execution-1",
    replay_type: "generate",
    model_name: "gpt-test",
    prompt_text: "prompt",
    response_text: "response",
    input_tokens: 100,
    output_tokens: 200,
    created_at: "2026-03-25T10:00:00Z",
    ...overrides,
  };
}

function createExecution(overrides: Partial<NodeExecutionView>): NodeExecutionView {
  return {
    id: "execution-1",
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
    ...overrides,
  };
}
