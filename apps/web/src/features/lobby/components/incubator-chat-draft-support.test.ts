import assert from "node:assert/strict";
import test from "node:test";

import type { ProjectIncubatorConversationDraft } from "@/lib/api/types";

import {
  buildDraftAiCompletionPrompt,
  buildDraftGuidance,
  shouldOfferDraftAiCompletion,
} from "./incubator-chat-draft-support";

test("incubator chat draft support marks warning drafts as directly usable", () => {
  const draft: ProjectIncubatorConversationDraft = {
    follow_up_questions: [
      "你希望整体基调或文风更偏什么感觉？",
      "这本书大概准备写多少字，或者规划多少章？",
    ],
    project_setting: {
      core_conflict: "主角在旧城区守住最后一家书店。",
      genre: "都市治愈",
      protagonist: { goal: "守住书店" },
      world_setting: { era_baseline: "当代城市老街更新期" },
    },
    setting_completeness: {
      issues: [
        { field: "tone", level: "warning", message: "缺少基调/风格" },
        { field: "scale", level: "warning", message: "缺少目标篇幅或章节规模" },
      ],
      status: "warning",
    },
  };

  assert.deepEqual(buildDraftGuidance(draft), {
    actionLabel: "让 AI 补齐这些内容",
    detail: "当前缺少 整体气质、篇幅规划。这不影响创建项目，也不影响后面继续用 AI 生成大纲。",
    statusLabel: "可继续",
    summary: "现在就能继续，剩下的是可补可不补的建议项。",
  });
  assert.equal(shouldOfferDraftAiCompletion(draft), true);
  assert.match(buildDraftAiCompletionPrompt(draft), /不要再让我自己填表/);
  assert.match(buildDraftAiCompletionPrompt(draft), /整体气质、篇幅规划/);
});

test("incubator chat draft support marks blocked drafts as needing AI completion first", () => {
  const draft: ProjectIncubatorConversationDraft = {
    follow_up_questions: ["主角现在最想达成什么？"],
    project_setting: {
      genre: "都市",
      protagonist: { identity: "旧书店店主" },
    },
    setting_completeness: {
      issues: [
        { field: "protagonist.goal", level: "blocked", message: "缺少主角核心目标" },
        { field: "core_conflict", level: "blocked", message: "缺少核心冲突" },
      ],
      status: "blocked",
    },
  };

  assert.deepEqual(buildDraftGuidance(draft), {
    actionLabel: "让 AI 先补一版",
    detail: "还差 主角设定、核心冲突。你不用自己填，点一下就能让 AI 先补成可继续创作的一版。",
    statusLabel: "待补全",
    summary: "还差关键信息，补一下再继续会更顺。",
  });
});
