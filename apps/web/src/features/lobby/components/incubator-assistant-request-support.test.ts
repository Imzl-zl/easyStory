import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "@/lib/api/client";

import {
  buildAssistantRetryFailure,
  buildAssistantStreamRecoveryNotice,
  buildIncubatorAssistantTurnPayload,
  shouldRetryAssistantWithoutStream,
} from "./incubator-assistant-request-support";
import { createIncubatorInitialMessages, type IncubatorChatSettings } from "./incubator-chat-support";

const SETTINGS: IncubatorChatSettings = {
  allowSystemCredentialPool: false,
  maxOutputTokens: "8192",
  modelName: "gpt-4.1",
  provider: "openai",
  streamOutput: true,
};

test("incubator assistant request support builds payload with explicit max tokens", () => {
  const payload = buildIncubatorAssistantTurnPayload(SETTINGS, createIncubatorInitialMessages());
  assert.deepEqual(payload.model, {
    max_tokens: 8192,
    name: "gpt-4.1",
    provider: "openai",
  });
  assert.equal(payload.skill_id, "skill.assistant.general_chat");
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
