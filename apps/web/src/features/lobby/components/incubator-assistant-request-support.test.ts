import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "@/lib/api/client";

import {
  buildAssistantRetryFailure,
  buildAssistantStreamRecoveryNotice,
  buildIncubatorAssistantTurnPayload,
  shouldRetryAssistantWithoutStream,
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

test("incubator assistant request support skips retry for clear client errors", () => {
  assert.equal(
    shouldRetryAssistantWithoutStream(new ApiError("参数非法", 422, "参数非法")),
    false,
  );
  assert.equal(
    shouldRetryAssistantWithoutStream(new ApiError("上游超时", 504, "上游超时")),
    true,
  );
});

test("incubator assistant request support builds readable recovery copy", () => {
  assert.match(buildAssistantStreamRecoveryNotice(), /自动改为完整返回/);
  assert.match(
    buildAssistantRetryFailure(new Error("第一次失败"), new Error("第二次失败")).message,
    /第一次错误：第一次失败；重试错误：第二次失败/,
  );
});
