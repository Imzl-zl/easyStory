import assert from "node:assert/strict";
import test from "node:test";
import type { UseMutationResult } from "@tanstack/react-query";

import type { AssistantTurnResult } from "@/lib/api/types";

import {
  completePromptSubmission,
  type PromptSubmission,
} from "./incubator-chat-submit-support";
import {
  createIncubatorInitialMessages,
  createIncubatorMessage,
} from "./incubator-chat-support";
import { createEmptyIncubatorChatSession } from "./incubator-chat-store";

test("incubator chat submit support records latest completed run id after success", async () => {
  const userMessage = createIncubatorMessage("user", "先给我一个故事方向");
  const pendingAssistant = createIncubatorMessage("assistant", "正在整理故事方向…", {
    status: "pending",
  });
  const submission: PromptSubmission = {
    conversationId: "conversation-incubator-1",
    nextMessages: [...createIncubatorInitialMessages(), userMessage, pendingAssistant],
    pendingAssistant,
    submittedMessages: [...createIncubatorInitialMessages(), userMessage],
  };
  const result: AssistantTurnResult = {
    run_id: "run-incubator-1",
    conversation_id: "conversation-incubator-1",
    client_turn_id: userMessage.id,
    agent_id: null,
    skill_id: null,
    provider: "openai",
    model_name: "gpt-5.4",
    content: "先从一个更清晰的主角欲望切进去。",
    output_items: [],
    output_meta: {},
    hook_results: [],
    mcp_servers: [],
    input_tokens: 10,
    output_tokens: 20,
    total_tokens: 30,
  };
  const assistantMutation = {
    mutateAsync: async () => result,
  } as UseMutationResult<AssistantTurnResult, unknown, PromptSubmission>;
  let nextSession = createEmptyIncubatorChatSession();

  await completePromptSubmission(
    assistantMutation,
    (conversationId, updater) => {
      assert.equal(conversationId, "conversation-incubator-1");
      nextSession = updater(nextSession);
    },
    submission,
  );

  assert.equal(nextSession.latestCompletedRunId, "run-incubator-1");
  assert.equal(nextSession.messages.at(-1)?.role, "assistant");
  assert.equal(nextSession.messages.at(-1)?.content, "先从一个更清晰的主角欲望切进去。");
});
