import assert from "node:assert/strict";
import test from "node:test";

import { createStudioChatMessage } from "./studio-chat-support";
import { createEmptyStudioChatSession } from "./studio-chat-store-support";
import { buildSucceededStudioConversationSession } from "./studio-chat-turn-support";

test("studio chat model clears one-time skill only after a successful turn", () => {
  const userMessage = createStudioChatMessage("user", "继续写");
  const pendingAssistantMessage = createStudioChatMessage("assistant", "正在回复…", {
    status: "pending",
    toolProgress: [{
      detail: "设定/人物.md",
      label: "读取文稿",
      statusLabel: "已完成",
      toolCallId: "call-1",
      tone: "success",
    }],
  });
  const session = {
    ...createEmptyStudioChatSession(),
    conversationSkillId: "skill.user.long-form",
    messages: [userMessage, pendingAssistantMessage],
    nextTurnSkillId: "skill.user.one-shot",
  };

  const nextSession = buildSucceededStudioConversationSession(session, {
    consumedNextTurnSkillId: session.nextTurnSkillId,
    content: "这次先把冲突压到更近的场景里。",
    messageId: pendingAssistantMessage.id,
    runId: "run-1",
  });

  assert.equal(nextSession.latestCompletedRunId, "run-1");
  assert.equal(nextSession.nextTurnSkillId, null);
  assert.equal(nextSession.conversationSkillId, "skill.user.long-form");
  assert.equal(nextSession.messages.at(-1)?.status, undefined);
  assert.equal(nextSession.messages.at(-1)?.content, "这次先把冲突压到更近的场景里。");
  assert.equal(nextSession.messages.at(-1)?.requestContent, "这次先把冲突压到更近的场景里。");
  assert.deepEqual(nextSession.messages.at(-1)?.toolProgress, pendingAssistantMessage.toolProgress);
});

test("studio chat model keeps next-turn skill untouched when this turn did not consume one", () => {
  const pendingAssistantMessage = createStudioChatMessage("assistant", "正在回复…", {
    status: "pending",
  });
  const session = {
    ...createEmptyStudioChatSession(),
    messages: [pendingAssistantMessage],
    nextTurnSkillId: "skill.user.one-shot",
  };

  const nextSession = buildSucceededStudioConversationSession(session, {
    consumedNextTurnSkillId: null,
    content: "保持当前对话模式。",
    messageId: pendingAssistantMessage.id,
    runId: "run-2",
  });

  assert.equal(nextSession.latestCompletedRunId, "run-2");
  assert.equal(nextSession.nextTurnSkillId, "skill.user.one-shot");
});
