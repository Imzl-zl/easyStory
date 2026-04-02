import assert from "node:assert/strict";
import test from "node:test";

import {
  buildProjectSettingConversationSeed,
  buildProjectSettingIssueSummary,
} from "@/features/project/components/project-setting-summary-support";

test("buildProjectSettingConversationSeed flattens existing summary into editable text", () => {
  assert.equal(
    buildProjectSettingConversationSeed({
      core_conflict: "旧书店与城市更新计划正面冲突。",
      genre: "都市治愈",
      protagonist: {
        goal: "守住书店",
        identity: "旧书店店主",
      },
      world_setting: {
        era_baseline: "当代旧城区更新期",
      },
    }),
    [
      "基础设定",
      "- 题材：都市治愈",
      "- 核心冲突：旧书店与城市更新计划正面冲突。",
      "",
      "主角",
      "- 身份：旧书店店主",
      "- 目标：守住书店",
      "",
      "世界",
      "- 时代基线：当代旧城区更新期",
    ].join("\n"),
  );
});

test("buildProjectSettingIssueSummary falls back to empty message when there are no issues", () => {
  assert.equal(
    buildProjectSettingIssueSummary({ issues: [], status: "ready" }, "当前摘要已完整。"),
    "当前摘要已完整。",
  );
});
