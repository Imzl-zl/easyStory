import assert from "node:assert/strict";
import test from "node:test";

import {
  listEngineDetailTabs,
  resolveEngineDetailTab,
} from "./engine-detail-panel-support";

test("listEngineDetailTabs returns stable chinese labels for user-facing tabs", () => {
  assert.deepEqual(listEngineDetailTabs(), [
    { key: "overview", label: "执行概览" },
    { key: "tasks", label: "章节任务" },
    { key: "reviews", label: "审核" },
    { key: "billing", label: "账单" },
    { key: "logs", label: "日志" },
    { key: "context", label: "上下文" },
    { key: "replays", label: "Prompt 回放" },
  ]);
});

test("resolveEngineDetailTab falls back to overview for missing or invalid tabs", () => {
  assert.equal(resolveEngineDetailTab(null), "overview");
  assert.equal(resolveEngineDetailTab(""), "overview");
  assert.equal(resolveEngineDetailTab("unknown"), "overview");
  assert.equal(resolveEngineDetailTab("logs"), "logs");
  assert.equal(resolveEngineDetailTab("tasks"), "tasks");
});
