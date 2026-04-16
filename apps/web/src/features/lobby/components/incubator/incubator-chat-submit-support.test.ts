import assert from "node:assert/strict";
import test from "node:test";
import type { UseMutationResult } from "@tanstack/react-query";

import type { AssistantTurnResult } from "@/lib/api/types";

import {
  completePromptSubmission,
  handlePromptSubmissionError,
  type PromptSubmission,
} from "@/features/lobby/components/incubator/incubator-chat-submit-support";
import {
  createIncubatorInitialMessages,
  createIncubatorMessage,
} from "@/features/lobby/components/incubator/incubator-chat-support";
import { createEmptyIncubatorChatSession, type IncubatorChatSession } from "@/features/lobby/components/incubator/incubator-chat-store";

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
  } as unknown as UseMutationResult<AssistantTurnResult, unknown, PromptSubmission>;
  let nextSession: IncubatorChatSession = createEmptyIncubatorChatSession();

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

test("incubator chat submit support clears latest completed run id after failure", () => {
  const userMessage = createIncubatorMessage("user", "给我一个故事方向");
  const pendingAssistant = createIncubatorMessage("assistant", "先给你一个方向", {
    status: "pending",
  });
  const submission: PromptSubmission = {
    conversationId: "conversation-incubator-2",
    nextMessages: [...createIncubatorInitialMessages(), userMessage, pendingAssistant],
    pendingAssistant,
    submittedMessages: [...createIncubatorInitialMessages(), userMessage],
  };
  let nextSession: IncubatorChatSession = {
    ...createEmptyIncubatorChatSession(),
    latestCompletedRunId: "run-incubator-prev-1",
    messages: submission.nextMessages,
  };

  handlePromptSubmissionError(
    new Error("上游在输出尚未完成时提前停止了这次回复。"),
    (conversationId, updater) => {
      assert.equal(conversationId, "conversation-incubator-2");
      nextSession = updater(nextSession);
    },
    () => undefined,
    submission,
  );

  assert.equal(nextSession.latestCompletedRunId, null);
  assert.equal(nextSession.messages.at(-1)?.status, "error");
  assert.match(nextSession.messages.at(-1)?.content ?? "", /先给你一个方向/);
});

test("incubator chat submit support does not retain latest completed run id when successful reply is rendered as error guidance", async () => {
  const userMessage = createIncubatorMessage("user", "继续");
  const pendingAssistant = createIncubatorMessage("assistant", "正在整理故事方向…", {
    status: "pending",
  });
  const submission: PromptSubmission = {
    conversationId: "conversation-incubator-3",
    nextMessages: [...createIncubatorInitialMessages(), userMessage, pendingAssistant],
    pendingAssistant,
    submittedMessages: [...createIncubatorInitialMessages(), userMessage],
  };
  const result: AssistantTurnResult = {
    run_id: "run-incubator-retired-1",
    conversation_id: "conversation-incubator-3",
    client_turn_id: userMessage.id,
    agent_id: null,
    skill_id: null,
    provider: "openai",
    model_name: "gpt-5.4",
    content: "Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro in the latest version of Antigravity.",
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
  } as unknown as UseMutationResult<AssistantTurnResult, unknown, PromptSubmission>;
  let nextSession: IncubatorChatSession = createEmptyIncubatorChatSession();

  await completePromptSubmission(
    assistantMutation,
    (conversationId, updater) => {
      assert.equal(conversationId, "conversation-incubator-3");
      nextSession = updater(nextSession);
    },
    submission,
  );

  assert.equal(nextSession.latestCompletedRunId, null);
  assert.equal(nextSession.messages.at(-1)?.status, "error");
});
