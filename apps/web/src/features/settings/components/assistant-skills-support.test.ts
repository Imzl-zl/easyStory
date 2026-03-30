import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantSkillDocumentPreview,
  buildAssistantSkillListDescription,
  buildAssistantSkillPayload,
  createEmptyAssistantSkillDraft,
  isAssistantSkillDirty,
  parseAssistantSkillDocument,
} from "./assistant-skills-support";

test("assistant skills support creates a beginner-friendly draft template", () => {
  const draft = createEmptyAssistantSkillDraft();
  assert.equal(draft.enabled, true);
  assert.match(draft.content, /\{\{ user_input \}\}/);
  assert.match(draft.content, /每次只追问一个关键问题/);
});

test("assistant skills support builds normalized payloads", () => {
  const payload = buildAssistantSkillPayload({
    content: "  用户输入：{{ user_input }}  ",
    defaultMaxOutputTokens: " 4096 ",
    defaultModelName: " claude-sonnet-4 ",
    defaultProvider: " anthropic ",
    description: " 先陪我收拢方向 ",
    enabled: true,
    name: " 温柔开题 ",
  });

  assert.deepEqual(payload, {
    content: "用户输入：{{ user_input }}",
    default_max_output_tokens: 4096,
    default_model_name: "claude-sonnet-4",
    default_provider: "anthropic",
    description: "先陪我收拢方向",
    enabled: true,
    name: "温柔开题",
  });
});

test("assistant skills support builds markdown preview with quoted frontmatter strings", () => {
  const preview = buildAssistantSkillDocumentPreview(
    {
      content: "用户输入：{{ user_input }}",
      defaultMaxOutputTokens: "4096",
      defaultModelName: "claude-sonnet-4",
      defaultProvider: "anthropic",
      description: "适合先聊方向：慢一点追问",
      enabled: true,
      name: "故事方向助手",
    },
    { skillId: "skill.user.story-helper-abc123" },
  );

  assert.match(preview, /^---/);
  assert.match(preview, /id: skill\.user\.story-helper-abc123/);
  assert.match(preview, /name: "故事方向助手"/);
  assert.match(preview, /description: "适合先聊方向：慢一点追问"/);
  assert.match(preview, /provider: "anthropic"/);
  assert.match(preview, /name: "claude-sonnet-4"/);
  assert.match(preview, /max_tokens: 4096/);
});

test("assistant skills support parses markdown documents back into drafts", () => {
  const parsed = parseAssistantSkillDocument(`---
name: "故事方向助手"
enabled: true
description: "适合先聊方向"
model:
  provider: "anthropic"
  name: "claude-sonnet-4"
  max_tokens: 4096
---

用户输入：{{ user_input }}`);

  assert.deepEqual(parsed, {
    content: "用户输入：{{ user_input }}",
    defaultMaxOutputTokens: "4096",
    defaultModelName: "claude-sonnet-4",
    defaultProvider: "anthropic",
    description: "适合先聊方向",
    enabled: true,
    name: "故事方向助手",
  });
});

test("assistant skills support summarizes disabled and missing descriptions", () => {
  assert.equal(buildAssistantSkillListDescription({ description: null, enabled: false }), "已停用");
  assert.equal(buildAssistantSkillListDescription({ description: null, enabled: true }), "聊天里可直接切换");
});

test("assistant skills support treats the starter draft as clean in create mode", () => {
  assert.equal(isAssistantSkillDirty(createEmptyAssistantSkillDraft(), null), false);
});
