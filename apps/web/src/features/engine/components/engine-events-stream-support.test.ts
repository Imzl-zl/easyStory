import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "@/lib/api/client";
import {
  isClientStreamError,
  mergeExecutionLogs,
  resolveClientStreamErrorMessage,
  upsertExecutionLog,
} from "./engine-events-stream-support";

type ExecutionLog = Parameters<typeof mergeExecutionLogs>[0][number];

test("mergeExecutionLogs keeps latest copy for duplicate ids and sorts by created_at desc", () => {
  const result = mergeExecutionLogs(
    [
      createLog({
        id: "log-1",
        created_at: "2026-03-25T10:00:00.000Z",
        message: "snapshot old",
      }),
    ],
    [
      createLog({
        id: "log-1",
        created_at: "2026-03-25T10:05:00.000Z",
        message: "local new",
      }),
      createLog({
        id: "log-2",
        created_at: "2026-03-25T10:03:00.000Z",
        message: "local second",
      }),
    ],
  );

  assert.deepEqual(
    result.map((item) => [item.id, item.message]),
    [
      ["log-1", "local new"],
      ["log-2", "local second"],
    ],
  );
});

test("upsertExecutionLog replaces existing log and keeps newest first", () => {
  const result = upsertExecutionLog(
    [
      createLog({
        id: "log-1",
        created_at: "2026-03-25T10:00:00.000Z",
        message: "old",
      }),
    ],
    createLog({
      id: "log-1",
      created_at: "2026-03-25T10:10:00.000Z",
      message: "new",
    }),
  );

  assert.equal(result.length, 1);
  assert.equal(result[0]?.message, "new");
});

test("resolveClientStreamErrorMessage reuses ApiError detail when available", () => {
  const message = resolveClientStreamErrorMessage(
    new ApiError("资源不存在或无权访问", 404, "资源不存在或无权访问"),
  );

  assert.equal(message, "实时连接失败：资源不存在或无权访问");
});

test("isClientStreamError only treats 4xx ApiError as client-side stream errors", () => {
  assert.equal(isClientStreamError(new ApiError("bad request", 400, null)), true);
  assert.equal(isClientStreamError(new ApiError("server error", 500, null)), false);
  assert.equal(isClientStreamError(new Error("network down")), false);
});

function createLog(overrides: Partial<ExecutionLog>): ExecutionLog {
  return {
    id: "log-0",
    workflow_execution_id: "workflow-1",
    node_execution_id: null,
    level: "INFO",
    message: "message",
    details: null,
    created_at: "2026-03-25T10:00:00.000Z",
    ...overrides,
  };
}
