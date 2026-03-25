import assert from "node:assert/strict";
import test from "node:test";

import type { ChapterTaskDraft, ChapterTaskView } from "@/lib/api/types";

import {
  buildRegenerateConfirmationItems,
  REGENERATE_CONFIRMATION_MESSAGE,
} from "./engine-task-regenerate-support";

test("REGENERATE_CONFIRMATION_MESSAGE keeps the documented destructive warning copy", () => {
  assert.equal(
    REGENERATE_CONFIRMATION_MESSAGE,
    "重建将覆盖当前章节计划，已生成的草稿将被标记为失效。",
  );
});

test("buildRegenerateConfirmationItems summarizes replacement impact for existing tasks", () => {
  assert.deepEqual(
    buildRegenerateConfirmationItems(
      [
        createTask({ chapter_number: 1, status: "completed" }),
        createTask({ chapter_number: 2, status: "stale" }),
        createTask({ chapter_number: 3, status: "stale" }),
      ],
      [createDraft(1), createDraft(2), createDraft(3), createDraft(4)],
    ),
    [
      "即将提交 4 条章节任务草稿。",
      "本次重建范围为第 1 至第 4 章。",
      "现有 3 条章节任务会被整体覆盖。",
      "其中 2 条已失效任务会被新计划替换。",
    ],
  );
});

test("buildRegenerateConfirmationItems explains direct creation when no current tasks exist", () => {
  assert.deepEqual(buildRegenerateConfirmationItems([], [createDraft(7)]), [
    "即将提交 1 条章节任务草稿。",
    "本次重建范围为第 7 章。",
    "当前 workflow 还没有章节任务真值，本次会直接建立新的章节计划。",
  ]);
});

function createDraft(chapterNumber: number): ChapterTaskDraft {
  return {
    brief: `brief-${chapterNumber}`,
    chapter_number: chapterNumber,
    key_characters: [],
    key_events: [],
    title: `title-${chapterNumber}`,
  };
}

function createTask(overrides: Partial<ChapterTaskView>): ChapterTaskView {
  return {
    brief: "brief",
    chapter_number: 1,
    content_id: null,
    key_characters: [],
    key_events: [],
    project_id: "project-1",
    status: "pending",
    task_id: "task-1",
    title: "title",
    workflow_execution_id: "workflow-1",
    ...overrides,
  };
}
