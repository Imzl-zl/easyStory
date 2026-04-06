import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIncubatorAssistantTurnPayload,
} from "./incubator-assistant-request-support";
import {
  createIncubatorInitialMessages,
  createIncubatorMessage,
  type IncubatorChatSettings,
} from "./incubator-chat-support";

const SETTINGS: IncubatorChatSettings = {
  agentId: "",
  allowSystemCredentialPool: false,
  hookIds: ["hook.user.story-summary", "hook.user.after-polish"],
  maxOutputTokens: "8192",
  modelName: "gpt-4.1",
  provider: "openai",
  skillId: "",
  streamOutput: true,
};

test("incubator assistant request support builds payload with explicit max tokens", () => {
  const payload = buildIncubatorAssistantTurnPayload({
    conversationId: "conv-incubator-1",
    latestCompletedRunId: null,
    messages: [...createIncubatorInitialMessages(), createIncubatorMessage("user", "先给我一个方向")],
    settings: SETTINGS,
  });
  assert.deepEqual(payload.model, {
    max_tokens: 8192,
    name: "gpt-4.1",
    provider: "openai",
  });
  assert.equal(payload.conversation_id, "conv-incubator-1");
  assert.equal(payload.client_turn_id.startsWith("user-"), true);
  assert.deepEqual(payload.hook_ids, ["hook.user.after-polish", "hook.user.story-summary"]);
  assert.equal(payload.requested_write_scope, "disabled");
  assert.equal(payload.messages.length, 2);
  assert.equal(payload.messages[0]?.role, "assistant");
  assert.equal(payload.messages[1]?.role, "user");
  assert.equal("skill_id" in payload, false);
});

test("incubator assistant request support prefers agent id when selected", () => {
  const payload = buildIncubatorAssistantTurnPayload({
    conversationId: "conv-incubator-2",
    latestCompletedRunId: null,
    messages: [...createIncubatorInitialMessages(), createIncubatorMessage("user", "我想写校园故事")],
    settings: { ...SETTINGS, agentId: "agent.user.story-coach-a1b2c3" },
  });
  assert.equal(payload.agent_id, "agent.user.story-coach-a1b2c3");
  assert.equal("skill_id" in payload, false);
});

test("incubator assistant request support drops legacy system messages from payload", () => {
  const payload = buildIncubatorAssistantTurnPayload({
    conversationId: "conv-incubator-3",
    latestCompletedRunId: null,
    messages: [
      ...createIncubatorInitialMessages(),
      { ...createIncubatorMessage("assistant", "旧隐藏指令"), role: "system" as never, hidden: true },
      createIncubatorMessage("user", "帮我想一个开头"),
    ] as unknown as ReturnType<typeof createIncubatorInitialMessages>,
    settings: SETTINGS,
  });

  assert.deepEqual(
    payload.messages.map((message) => message.role),
    ["assistant", "user"],
  );
});

test("incubator assistant request support carries previous completed run id into continuation anchor", () => {
  const payload = buildIncubatorAssistantTurnPayload({
    conversationId: "conv-incubator-4",
    latestCompletedRunId: "run-prev-1",
    messages: [...createIncubatorInitialMessages(), createIncubatorMessage("user", "继续往下收束设定")],
    settings: SETTINGS,
  });

  assert.deepEqual(payload.continuation_anchor, {
    previous_run_id: "run-prev-1",
  });
});

test("incubator assistant request support requires the last message to be from the user", () => {
  const messages = [
    ...createIncubatorInitialMessages(),
    createIncubatorMessage("assistant", "先补一段"),
  ];

  assert.throws(
    () =>
      buildIncubatorAssistantTurnPayload({
        conversationId: "conv-incubator-5",
        latestCompletedRunId: null,
        messages,
        settings: SETTINGS,
      }),
    /latest user message/,
  );
});
