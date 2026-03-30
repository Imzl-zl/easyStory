import assert from "node:assert/strict";
import test from "node:test";

import {
  ASSISTANT_HOOK_ACTION_TYPE_OPTIONS,
  buildAssistantHookDocumentPreview,
  buildAssistantHookListDescription,
  buildAssistantHookPayload,
  createEmptyAssistantHookDraft,
  parseAssistantHookDocument,
  resolveAssistantHookEventLabel,
} from "./assistant-hooks-support";

test("assistant hooks support creates a beginner-friendly draft template", () => {
  const draft = createEmptyAssistantHookDraft();
  assert.equal(draft.enabled, true);
  assert.equal(draft.event, "after_assistant_response");
  assert.equal(draft.agentId, "");
  assert.equal(draft.actionType, "agent");
  assert.deepEqual(ASSISTANT_HOOK_ACTION_TYPE_OPTIONS.map((item) => item.value), ["agent", "mcp"]);
});

test("assistant hooks support builds normalized payloads", () => {
  const payload = buildAssistantHookPayload({
    actionType: "mcp",
    agentId: " agent.user.story-summary ",
    arguments: { limit: 3 },
    description: " 回复后帮我整理重点 ",
    enabled: true,
    event: "after_assistant_response",
    inputMapping: { query: " request.user_input " },
    name: " 自动整理 ",
    serverId: " mcp.user.story-tools ",
    toolName: " search_story ",
  });

  assert.deepEqual(payload, {
    action: {
      action_type: "mcp",
      arguments: { limit: 3 },
      input_mapping: { query: "request.user_input" },
      server_id: "mcp.user.story-tools",
      tool_name: "search_story",
    },
    description: "回复后帮我整理重点",
    enabled: true,
    event: "after_assistant_response",
    name: "自动整理",
  });
});

test("assistant hooks support builds yaml preview for HOOK file", () => {
  const preview = buildAssistantHookDocumentPreview(
    {
      actionType: "mcp",
      agentId: "agent.user.story-summary",
      arguments: { limit: 3 },
      description: "回复后帮我整理重点",
      enabled: true,
      event: "after_assistant_response",
      inputMapping: { query: "request.user_input" },
      name: "自动整理",
      serverId: "mcp.user.story-tools",
      toolName: "search_story",
    },
    { hookId: "hook.user.story-summary-abc123" },
  );

  assert.match(preview, /^hook:/);
  assert.match(preview, /id: hook\.user\.story-summary-abc123/);
  assert.match(preview, /name: "自动整理"/);
  assert.match(preview, /description: "回复后帮我整理重点"/);
  assert.match(preview, /event: after_assistant_response/);
  assert.match(preview, /type: mcp/);
  assert.match(preview, /server_id: mcp\.user\.story-tools/);
  assert.match(preview, /tool_name: "search_story"/);
});

test("assistant hooks support parses yaml documents back into drafts", () => {
  const parsed = parseAssistantHookDocument(`hook:
  name: "自动整理"
  enabled: true
  description: "回复后帮我整理重点"
  author: user
  trigger:
    event: after_assistant_response
    node_types: []
  action:
    type: mcp
    config:
      server_id: mcp.user.story-tools
      tool_name: "search_story"
      arguments: {"limit":3}
      input_mapping: {"query":"request.user_input"}
  priority: 10
  timeout: 30`);

  assert.deepEqual(parsed, {
    actionType: "mcp",
    agentId: "",
    arguments: { limit: 3 },
    description: "回复后帮我整理重点",
    enabled: true,
    event: "after_assistant_response",
    inputMapping: { query: "request.user_input" },
    name: "自动整理",
    serverId: "mcp.user.story-tools",
    toolName: "search_story",
  });
});

test("assistant hooks support summarizes default descriptions with event label", () => {
  assert.equal(
    buildAssistantHookListDescription(
      {
        action: {
          action_type: "agent",
          agent_id: "agent.user.story-summary",
          input_mapping: {},
        },
        description: null,
        enabled: true,
        event: "after_assistant_response",
      },
      { agentLabel: "故事摘要 Agent" },
    ),
    "回复后自动处理 · 故事摘要 Agent",
  );
  assert.equal(
    buildAssistantHookListDescription(
      {
        action: {
          action_type: "mcp",
          arguments: {},
          input_mapping: {},
          server_id: "mcp.user.story-tools",
          tool_name: "search_story",
        },
        description: null,
        enabled: true,
        event: "before_assistant_response",
      },
      { mcpLabel: "资料检索" },
    ),
    "回复前先处理 · 资料检索 · search_story",
  );
  assert.equal(resolveAssistantHookEventLabel("before_assistant_response"), "回复前先处理");
});
