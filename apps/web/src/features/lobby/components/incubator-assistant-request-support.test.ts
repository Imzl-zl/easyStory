import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIncubatorAssistantTurnPayload,
} from "./incubator-assistant-request-support";
import {
  createIncubatorInitialMessages,
  INCUBATOR_CHAT_SKILL_ID,
  type IncubatorChatSettings,
} from "./incubator-chat-support";

const SETTINGS: IncubatorChatSettings = {
  agentId: "",
  allowSystemCredentialPool: false,
  hookIds: ["hook.user.story-summary", "hook.user.after-polish"],
  maxOutputTokens: "8192",
  modelName: "gpt-4.1",
  provider: "openai",
  skillId: INCUBATOR_CHAT_SKILL_ID,
  streamOutput: true,
};

test("incubator assistant request support builds payload with explicit max tokens", () => {
  const payload = buildIncubatorAssistantTurnPayload(SETTINGS, createIncubatorInitialMessages());
  assert.deepEqual(payload.model, {
    max_tokens: 8192,
    name: "gpt-4.1",
    provider: "openai",
  });
  assert.deepEqual(payload.hook_ids, ["hook.user.after-polish", "hook.user.story-summary"]);
  assert.equal(payload.skill_id, INCUBATOR_CHAT_SKILL_ID);
});

test("incubator assistant request support prefers agent id when selected", () => {
  const payload = buildIncubatorAssistantTurnPayload(
    { ...SETTINGS, agentId: "agent.user.story-coach-a1b2c3" },
    createIncubatorInitialMessages(),
  );
  assert.equal(payload.agent_id, "agent.user.story-coach-a1b2c3");
  assert.equal("skill_id" in payload, false);
});
