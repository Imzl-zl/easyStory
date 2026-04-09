import assert from "node:assert/strict";
import test from "node:test";

import { STUDIO_PENDING_REPLY_MESSAGE } from "@/features/studio/components/chat/studio-chat-support";
import {
  createConversationForProjectState,
  normalizePersistedStudioChatProjectState,
  patchConversationInProjectState,
} from "@/features/studio/components/chat/studio-chat-store-support";

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
          reasoningEffort: "",
          streamOutput: true,
          thinkingBudget: "",
          thinkingLevel: "",
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
    reasoningEffort: "",
    streamOutput: true,
    thinkingBudget: "",
    thinkingLevel: "",
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
          reasoningEffort: "",
          streamOutput: true,
          thinkingBudget: "",
          thinkingLevel: "",
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
          reasoningEffort: "",
          streamOutput: true,
          thinkingBudget: "",
          thinkingLevel: "",
        },
      },
      title: "测试",
      updatedAt: "2026-04-08T12:00:00Z",
    }],
  });

  assert.equal(normalized.conversations[0]?.session.latestCompletedRunId, null);
});

test("studio chat store can patch session without refreshing updatedAt ordering", () => {
  const projectState = {
    activeConversationId: "conversation-old",
    conversations: [{
      id: "conversation-new",
      session: {
        composerText: "",
        conversationSkillId: null,
        latestCompletedRunId: null,
        messages: [{
          content: "最近一条",
          id: "user-new",
          rawMarkdown: "最近一条",
          role: "user" as const,
        }],
        nextTurnSkillId: null,
        selectedContextPaths: [],
        settings: {
          maxOutputTokens: "",
          modelName: "",
          provider: "",
          reasoningEffort: "",
          streamOutput: true,
          thinkingBudget: "",
          thinkingLevel: "",
        },
      },
      title: "最近会话",
      updatedAt: "2026-04-08T12:00:00Z",
    }, {
      id: "conversation-old",
      session: {
        composerText: "",
        conversationSkillId: "skill.user.missing-helper",
        latestCompletedRunId: null,
        messages: [{
          content: "旧会话",
          id: "user-old",
          rawMarkdown: "旧会话",
          role: "user" as const,
        }],
        nextTurnSkillId: null,
        selectedContextPaths: [],
        settings: {
          maxOutputTokens: "",
          modelName: "",
          provider: "",
          reasoningEffort: "",
          streamOutput: true,
          thinkingBudget: "",
          thinkingLevel: "",
        },
      },
      title: "旧会话",
      updatedAt: "2026-04-08T10:00:00Z",
    }],
  };

  const nextState = patchConversationInProjectState(
    projectState,
    "conversation-old",
    (current) => ({
      ...current,
      conversationSkillId: null,
    }),
    { preserveUpdatedAt: true },
  );

  assert.deepEqual(nextState.conversations.map((item) => item.id), [
    "conversation-new",
    "conversation-old",
  ]);
  assert.equal(nextState.conversations[1]?.updatedAt, "2026-04-08T10:00:00.000Z");
  assert.equal(nextState.conversations[1]?.session.conversationSkillId, null);
});
