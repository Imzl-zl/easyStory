import assert from "node:assert/strict";
import test from "node:test";

import { createStudioChatMessage } from "./studio-chat-support";
import { createEmptyStudioChatSession } from "./studio-chat-store-support";
import { buildSucceededStudioConversationSession } from "./studio-chat-turn-support";

test("studio chat model clears one-time skill only after a successful turn", () => {
  const userMessage = createStudioChatMessage("user", "继续写");
  const pendingAssistantMessage = createStudioChatMessage("assistant", "正在回复…", {
    status: "pending",
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
  });

  assert.equal(nextSession.nextTurnSkillId, null);
  assert.equal(nextSession.conversationSkillId, "skill.user.long-form");
  assert.equal(nextSession.messages.at(-1)?.status, undefined);
  assert.equal(nextSession.messages.at(-1)?.content, "这次先把冲突压到更近的场景里。");
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
  });

  assert.equal(nextSession.nextTurnSkillId, "skill.user.one-shot");
});
