import assert from "node:assert/strict";
import test from "node:test";

import { STUDIO_PENDING_REPLY_MESSAGE } from "./studio-chat-support";
import {
  createConversationForProjectState,
  normalizePersistedStudioChatProjectState,
} from "./studio-chat-store-support";

test("studio chat store keeps provider settings when creating a new conversation", () => {
  const nextState = createConversationForProjectState({
    activeConversationId: "conversation-1",
    conversations: [{
      id: "conversation-1",
      session: {
        composerText: "",
        conversationSkillId: null,
        latestCompletedRunId: null,
        messages: [{
          content: "继续写第三章",
          id: "user-1",
          rawMarkdown: "继续写第三章",
          role: "user",
        }],
        nextTurnSkillId: null,
        selectedContextPaths: [],
        settings: {
          maxOutputTokens: "4096",
          modelName: "gemini-2.5-flash",
          provider: "mint",
          streamOutput: true,
        },
      },
      title: "第三章推进",
      updatedAt: "2026-04-08T12:00:00Z",
    }],
  });

  const createdConversation = nextState.conversations[0];
  assert.equal(nextState.activeConversationId, createdConversation?.id);
  assert.deepEqual(createdConversation?.session.settings, {
    maxOutputTokens: "4096",
    modelName: "gemini-2.5-flash",
    provider: "mint",
    streamOutput: true,
  });
  assert.deepEqual(createdConversation?.session.messages, []);
  assert.deepEqual(createdConversation?.session.selectedContextPaths, []);
  assert.equal(createdConversation?.session.conversationSkillId, null);
  assert.equal(createdConversation?.session.nextTurnSkillId, null);
});

test("studio chat store preserves tool progress when persisted pending reply is restored", () => {
  const normalized = normalizePersistedStudioChatProjectState({
    activeConversationId: "conversation-1",
    conversations: [{
      id: "conversation-1",
      session: {
        composerText: "",
        conversationSkillId: null,
        latestCompletedRunId: "run-studio-prev-1",
        messages: [{
          content: STUDIO_PENDING_REPLY_MESSAGE,
          id: "assistant-1",
          rawMarkdown: STUDIO_PENDING_REPLY_MESSAGE,
          role: "assistant",
          status: "pending",
          toolProgress: [{
            detail: "设定/人物.md",
            label: "读取文稿",
            statusLabel: "处理中",
            toolCallId: "call-1",
            tone: "running",
          }],
        }],
        nextTurnSkillId: null,
        selectedContextPaths: [],
        settings: {
          maxOutputTokens: "",
          modelName: "",
          provider: "",
          streamOutput: true,
        },
      },
      title: "测试",
      updatedAt: "2026-04-08T12:00:00Z",
    }],
  });

  assert.equal(normalized.conversations[0]?.session.latestCompletedRunId, null);
  const restoredMessage = normalized.conversations[0]?.session.messages[0];
  assert.equal(restoredMessage?.status, "error");
  assert.equal(restoredMessage?.content, "这次回复中断了，你可以重新发送。");
  assert.deepEqual(restoredMessage?.toolProgress, [{
    detail: "设定/人物.md",
    label: "读取文稿",
    statusLabel: "已中断",
    toolCallId: "call-1",
    tone: "muted",
  }]);
});

test("studio chat store clears latest completed run id when restored conversation ends with failed reply", () => {
  const normalized = normalizePersistedStudioChatProjectState({
    activeConversationId: "conversation-1",
    conversations: [{
      id: "conversation-1",
      session: {
        composerText: "",
        conversationSkillId: null,
        latestCompletedRunId: "run-studio-prev-2",
        messages: [{
          content: "继续写第三章",
          id: "user-1",
          rawMarkdown: "继续写第三章",
          role: "user",
        }, {
          content: "这次回复中断了，你可以重新发送。",
          id: "assistant-1",
          rawMarkdown: "这次回复中断了，你可以重新发送。",
          role: "assistant",
          status: "error",
        }],
        nextTurnSkillId: null,
        selectedContextPaths: [],
        settings: {
          maxOutputTokens: "",
          modelName: "",
          provider: "",
          streamOutput: true,
        },
      },
      title: "测试",
      updatedAt: "2026-04-08T12:00:00Z",
    }],
  });

  assert.equal(normalized.conversations[0]?.session.latestCompletedRunId, null);
});
