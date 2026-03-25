import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExportPrecheck,
  resolveExportCreateDisabledReason,
  toggleExportFormat,
} from "./engine-export-support";

type ChapterTask = Parameters<typeof buildExportPrecheck>[0][number];

test("buildExportPrecheck blocks stale task without confirmed content", () => {
  const result = buildExportPrecheck([
    createTask({
      chapter_number: 3,
      content_id: null,
      status: "stale",
    }),
  ]);

  assert.equal(result.warningItems.length, 0);
  assert.equal(result.blockingItems.length, 1);
  assert.equal(result.blockingItems[0]?.chapterNumber, 3);
  assert.equal(result.blockingItems[0]?.title, "缺少已确认正文");
});

test("buildExportPrecheck keeps stale task with content as warning and skipped task as info", () => {
  const result = buildExportPrecheck([
    createTask({
      chapter_number: 1,
      content_id: "content-1",
      status: "stale",
    }),
    createTask({
      chapter_number: 2,
      status: "skipped",
    }),
  ]);

  assert.equal(result.blockingItems.length, 0);
  assert.equal(result.warningItems.length, 1);
  assert.equal(result.warningItems[0]?.chapterNumber, 1);
  assert.equal(result.infoItems.length, 1);
  assert.equal(result.infoItems[0]?.title, "章节已跳过");
});

test("resolveExportCreateDisabledReason follows workflow then task then format then blocking order", () => {
  assert.equal(
    resolveExportCreateDisabledReason({
      blockingCount: 0,
      hasWorkflow: false,
      selectedFormatsCount: 1,
      taskCount: 1,
    }),
    "请先载入一个 workflow，再从该工作流发起导出。",
  );
  assert.equal(
    resolveExportCreateDisabledReason({
      blockingCount: 0,
      hasWorkflow: true,
      selectedFormatsCount: 1,
      taskCount: 0,
    }),
    "当前 workflow 还没有章节任务真值，无法导出。",
  );
  assert.equal(
    resolveExportCreateDisabledReason({
      blockingCount: 0,
      hasWorkflow: true,
      selectedFormatsCount: 0,
      taskCount: 2,
    }),
    "至少选择一种导出格式。",
  );
  assert.equal(
    resolveExportCreateDisabledReason({
      blockingCount: 1,
      hasWorkflow: true,
      selectedFormatsCount: 1,
      taskCount: 2,
    }),
    "当前存在未完成章节，需先处理阻断项后再导出。",
  );
});

test("toggleExportFormat keeps configured export order", () => {
  const result = toggleExportFormat(["markdown"], "txt");

  assert.deepEqual(result, ["txt", "markdown"]);
});

function createTask(overrides: Partial<ChapterTask>): ChapterTask {
  return {
    task_id: "task-1",
    project_id: "project-1",
    workflow_execution_id: "workflow-1",
    chapter_number: 1,
    title: "第一章",
    brief: "章节简介",
    key_characters: [],
    key_events: [],
    status: "pending",
    content_id: null,
    ...overrides,
  };
}
