import assert from "node:assert/strict";
import test from "node:test";

import {
  createStudioChatMessage,
  resolveStudioPreparedAssistantTurnPayload,
} from "./studio-chat-support";
import { createEmptyStudioChatSession } from "./studio-chat-store-support";
import {
  buildFailedStudioConversationSession,
  buildSucceededStudioConversationSession,
} from "./studio-chat-turn-support";

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
  assert.equal(nextSession.messages.at(-1)?.rawMarkdown, "这次先把冲突压到更近的场景里。");
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

test("studio chat model clears latest completed run id after a failed turn", () => {
  const userMessage = createStudioChatMessage("user", "继续写这一段");
  const pendingAssistantMessage = createStudioChatMessage("assistant", "先补半句", {
    status: "pending",
    toolProgress: [{
      detail: "正文/第001章.md",
      label: "写入文稿",
      statusLabel: "处理中",
      toolCallId: "call-1",
      tone: "running",
    }],
  });
  const session = {
    ...createEmptyStudioChatSession(),
    latestCompletedRunId: "run-prev-1",
    messages: [userMessage, pendingAssistantMessage],
  };

  const nextSession = buildFailedStudioConversationSession(session, {
    errorMessage: "上游在输出尚未完成时提前停止了这次回复。",
    messageId: pendingAssistantMessage.id,
    terminalReason: "interrupted",
  });

  assert.equal(nextSession.latestCompletedRunId, null);
  assert.equal(nextSession.messages.at(-1)?.status, "error");
  assert.match(nextSession.messages.at(-1)?.content ?? "", /先补半句/);
  assert.equal(nextSession.messages.at(-1)?.rawMarkdown, nextSession.messages.at(-1)?.content);
  assert.equal(nextSession.messages.at(-1)?.requestContent, nextSession.messages.at(-1)?.content);
  assert.deepEqual(nextSession.messages.at(-1)?.toolProgress, [{
    detail: "正文/第001章.md",
    label: "写入文稿",
    statusLabel: "已中断",
    toolCallId: "call-1",
    tone: "muted",
  }]);
});

test("studio chat model does not retain latest completed run id when successful reply is rendered as error guidance", () => {
  const pendingAssistantMessage = createStudioChatMessage("assistant", "正在回复…", {
    status: "pending",
  });
  const session = {
    ...createEmptyStudioChatSession(),
    messages: [pendingAssistantMessage],
  };

  const nextSession = buildSucceededStudioConversationSession(session, {
    consumedNextTurnSkillId: null,
    content: "Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro in the latest version of Antigravity.",
    messageId: pendingAssistantMessage.id,
    runId: "run-retired-model-1",
  });

  assert.equal(nextSession.latestCompletedRunId, null);
  assert.equal(nextSession.messages.at(-1)?.status, "error");
  assert.equal(nextSession.messages.at(-1)?.rawMarkdown, nextSession.messages.at(-1)?.content);
  assert.equal(nextSession.messages.at(-1)?.requestContent, nextSession.messages.at(-1)?.content);
});

test("studio chat model prepares payload errors as explicit result instead of throwing", () => {
  const result = resolveStudioPreparedAssistantTurnPayload({
    activeBufferState: {
      base_version: "canonical:chapter:001:version:content-1:2",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    conversationId: "conversation-studio-stale-catalog",
    currentDocumentPath: "正文/第001章.md",
    latestCompletedRunId: null,
    messages: [createStudioChatMessage("user", "继续写这一段")],
    projectId: "project-1",
    selectedContextPaths: [],
    settings: {
      maxOutputTokens: "2000",
      modelName: "",
      provider: "",
      streamOutput: true,
    },
  });

  assert.equal(result.ok, false);
  if (result.ok) {
    throw new Error("expected payload preparation to fail");
  }
  assert.match(result.errorMessage, /目录快照尚未就绪/);
});

test("studio chat model payload helper rethrows unexpected preparation errors", () => {
  assert.throws(
    () => resolveStudioPreparedAssistantTurnPayload({
      conversationId: "conversation-studio-invalid-latest-message",
      currentDocumentPath: null,
      latestCompletedRunId: null,
      messages: [createStudioChatMessage("assistant", "我先补一句")],
      projectId: "project-1",
      selectedContextPaths: [],
      settings: {
        maxOutputTokens: "2000",
        modelName: "",
        provider: "",
        streamOutput: true,
      },
    }),
    /latest user message/,
  );
});
