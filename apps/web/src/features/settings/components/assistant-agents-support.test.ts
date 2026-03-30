import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantAgentDocumentPreview,
  buildAssistantAgentListDescription,
  buildAssistantAgentPayload,
  createEmptyAssistantAgentDraft,
  isAssistantAgentDirty,
  parseAssistantAgentDocument,
} from "./assistant-agents-support";

test("assistant agents support creates a beginner-friendly draft template", () => {
  const draft = createEmptyAssistantAgentDraft();
  assert.equal(draft.enabled, true);
  assert.equal(draft.skillId, "skill.assistant.general_chat");
  assert.match(draft.systemPrompt, /先给结论/);
});

test("assistant agents support does not treat the default create draft as dirty", () => {
  const draft = createEmptyAssistantAgentDraft();

  assert.equal(isAssistantAgentDirty(draft, null), false);
  assert.equal(
    isAssistantAgentDirty(
      {
        ...draft,
        name: "长期搭子",
      },
      null,
    ),
    true,
  );
});

test("assistant agents support builds normalized payloads", () => {
  const payload = buildAssistantAgentPayload({
    defaultMaxOutputTokens: " 4096 ",
    defaultModelName: " claude-sonnet-4 ",
    defaultProvider: " anthropic ",
    description: " 更像长期创作搭子 ",
    enabled: true,
    name: " 温柔陪跑 ",
    skillId: " skill.assistant.general_chat ",
    systemPrompt: " 先给结论，再慢慢展开。 ",
  });

  assert.deepEqual(payload, {
    default_max_output_tokens: 4096,
    default_model_name: "claude-sonnet-4",
    default_provider: "anthropic",
    description: "更像长期创作搭子",
    enabled: true,
    name: "温柔陪跑",
    skill_id: "skill.assistant.general_chat",
    system_prompt: "先给结论，再慢慢展开。",
  });
});

test("assistant agents support builds markdown preview with quoted frontmatter strings", () => {
  const preview = buildAssistantAgentDocumentPreview(
    {
      defaultMaxOutputTokens: "4096",
      defaultModelName: "claude-sonnet-4",
      defaultProvider: "anthropic",
      description: "更像长期创作搭子",
      enabled: true,
      name: "温柔陪跑",
      skillId: "skill.assistant.general_chat",
      systemPrompt: "先给结论，再慢慢展开。",
    },
    { agentId: "agent.user.story-coach-abc123" },
  );

  assert.match(preview, /^---/);
  assert.match(preview, /id: agent\.user\.story-coach-abc123/);
  assert.match(preview, /name: "温柔陪跑"/);
  assert.match(preview, /skill_id: skill\.assistant\.general_chat/);
  assert.match(preview, /description: "更像长期创作搭子"/);
  assert.match(preview, /provider: "anthropic"/);
  assert.match(preview, /name: "claude-sonnet-4"/);
  assert.match(preview, /max_tokens: 4096/);
});

test("assistant agents support parses markdown documents back into drafts", () => {
  const parsed = parseAssistantAgentDocument(`---
name: "温柔陪跑"
enabled: true
description: "更像长期创作搭子"
skill_id: skill.assistant.general_chat
model:
  provider: "anthropic"
  name: "claude-sonnet-4"
  max_tokens: 4096
---

先给结论，再慢慢展开。`);

  assert.deepEqual(parsed, {
    defaultMaxOutputTokens: "4096",
    defaultModelName: "claude-sonnet-4",
    defaultProvider: "anthropic",
    description: "更像长期创作搭子",
    enabled: true,
    name: "温柔陪跑",
    skillId: "skill.assistant.general_chat",
    systemPrompt: "先给结论，再慢慢展开。",
  });
});

test("assistant agents support summarizes disabled and missing descriptions", () => {
  assert.equal(
    buildAssistantAgentListDescription(
      { description: null, enabled: false, skill_id: "skill.assistant.general_chat" },
      "默认聊天助手",
    ),
    "已停用",
  );
  assert.equal(
    buildAssistantAgentListDescription(
      { description: null, enabled: true, skill_id: "skill.assistant.general_chat" },
      "默认聊天助手",
    ),
    "已绑定 默认聊天助手",
  );
});
