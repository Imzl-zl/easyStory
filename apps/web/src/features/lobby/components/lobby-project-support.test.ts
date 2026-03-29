import assert from "node:assert/strict";
import test from "node:test";

import type { ProjectSummary } from "@/lib/api/types";
import {
  buildFilteredProjects,
  formatProjectTargetWords,
  formatProjectTrashDeadline,
  formatProjectTrashTime,
  resolveEmptyTrashButtonLabel,
  resolveEmptyTrashNotice,
  resolveProjectActionButtonLabel,
  resolveProjectActionNotice,
} from "./lobby-project-support";

test("lobby project support filters by keyword and formats target words", () => {
  const projects: ProjectSummary[] = [
    {
      id: "1",
      name: "玄幻计划",
      status: "draft",
      genre: "玄幻",
      target_words: 120000,
      template_id: null,
      allow_system_credential_pool: false,
      deleted_at: null,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    },
    {
      id: "2",
      name: "都市悬疑",
      status: "draft",
      genre: "都市",
      target_words: null,
      template_id: null,
      allow_system_credential_pool: false,
      deleted_at: null,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    },
  ];

  assert.deepEqual(buildFilteredProjects(projects, "玄幻").map((item) => item.id), ["1"]);
  assert.equal(formatProjectTargetWords(null), "未设定");
  assert.equal(formatProjectTargetWords(120000), "120,000 字");
});

test("lobby project support formats trash time and deadline in UTC", () => {
  const deletedAt = "2026-03-01T08:30:00Z";

  assert.equal(formatProjectTrashTime(deletedAt), "03/01 08:30 UTC");
  assert.equal(formatProjectTrashDeadline(deletedAt), "03/31 08:30 UTC");
  assert.equal(formatProjectTrashDeadline(null), "暂无");
});

test("lobby project support resolves action and feedback copy", () => {
  assert.equal(resolveProjectActionButtonLabel("delete", false), "移入回收站");
  assert.equal(resolveProjectActionButtonLabel("restore", true), "恢复中...");
  assert.equal(resolveProjectActionButtonLabel("physicalDelete", false), "彻底删除");
  assert.deepEqual(resolveProjectActionNotice("physicalDelete"), {
    content: "项目已彻底删除。",
    title: "项目",
    tone: "success",
  });
  assert.equal(resolveEmptyTrashButtonLabel(true), "清空中...");
  assert.deepEqual(
    resolveEmptyTrashNotice({
      deleted_count: 0,
      skipped_count: 0,
      failed_count: 0,
      skipped_project_ids: [],
      failed_items: [],
    }),
    {
      content: "回收站已经是空的。",
      title: "回收站",
      tone: "info",
    },
  );
  assert.deepEqual(
    resolveEmptyTrashNotice({
      deleted_count: 3,
      skipped_count: 0,
      failed_count: 0,
      skipped_project_ids: [],
      failed_items: [],
    }),
    {
      content: "已清空回收站，共彻底删除 3 个项目。",
      title: "回收站",
      tone: "success",
    },
  );
  assert.deepEqual(
    resolveEmptyTrashNotice({
      deleted_count: 1,
      skipped_count: 1,
      failed_count: 1,
      skipped_project_ids: ["project-2"],
      failed_items: [{ project_id: "project-3", message: "项目清理失败" }],
    }),
    {
      content: "已彻底删除 1 个项目，跳过 1 个已恢复项目，另有 1 个项目清理异常。请稍后重试或查看后端日志。",
      title: "回收站",
      tone: "warning",
    },
  );
});
