import assert from "node:assert/strict";
import test from "node:test";

import type { ProjectPreparationStatus } from "@/lib/api/types";

import {
  buildPreparationStatusRows,
  describeAssetStatus,
  describeTaskStatus,
  formatPreparationNextStep,
  formatPreparationStatusLabel,
} from "./preparation-status-support";

test("buildPreparationStatusRows keeps setting and asset descriptions aligned with preparation truth", () => {
  const rows = buildPreparationStatusRows(
    createPreparationStatus({
      next_step: "outline",
      outline: {
        content_id: "outline-1",
        content_status: "approved",
        has_content: true,
        step_status: "approved",
        updated_at: "2026-03-25T10:00:00Z",
        version_number: 3,
      },
      setting: {
        issues: [{ field: "genre", level: "warning", message: "建议补齐题材倾向。" }],
        status: "warning",
      },
    }),
  );

  assert.deepEqual(rows, [
    {
      description: "建议补齐题材倾向。",
      label: "设定完整度",
      status: "warning",
    },
    {
      description: "当前为已确认版本，第 3 版。",
      label: "大纲",
      status: "approved",
    },
    {
      description: "前 1-3 章的阶段约束",
      label: "开篇设计",
      status: "not_started",
    },
    {
      description: "尚未生成章节任务。",
      label: "章节任务",
      status: "not_started",
    },
  ]);
});

test("describeTaskStatus exposes every non-zero task count including skipped", () => {
  const description = describeTaskStatus({
    counts: {
      completed: 2,
      failed: 1,
      generating: 1,
      interrupted: 1,
      pending: 3,
      skipped: 4,
      stale: 1,
    },
    step_status: "generating",
    total: 12,
    workflow_execution_id: "workflow-1",
  });

  assert.equal(
    description,
    "共 12 个任务 / 3 个未开始 / 1 个进行中 / 2 个已确认 / 1 个已失效 / 1 个失败 / 1 个已中断 / 4 个已跳过",
  );
});

test("format helpers map next step, status label and asset status consistently", () => {
  assert.equal(formatPreparationNextStep("opening_plan"), "开篇设计");
  assert.equal(formatPreparationStatusLabel("chapter_tasks"), "待任务");
  assert.equal(
    describeAssetStatus(
      {
        content_id: "opening-1",
        content_status: "stale",
        has_content: true,
        step_status: "stale",
        updated_at: "2026-03-25T12:00:00Z",
        version_number: 2,
      },
      "unused fallback",
    ),
    "上游真值已变化，当前内容已失效，需要重新检查或生成。",
  );
});

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
