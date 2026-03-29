import assert from "node:assert/strict";
import test from "node:test";

import {
  appendIncubatorMessageDelta,
  buildAssistantModelOverride,
  buildIncubatorConversationFingerprint,
  buildIncubatorConversationText,
  buildSuggestedProjectName,
  createIncubatorInitialMessages,
  createIncubatorMessage,
  INCUBATOR_DEFAULT_PROVIDER,
  INCUBATOR_INTERRUPTED_REPLY_MESSAGE,
  INCUBATOR_PENDING_REPLY_MESSAGE,
  resolveIncubatorAssistantReply,
  resolveChatOutputModeLabel,
  resolveInterruptedIncubatorReply,
  shouldShowPromptSuggestions,
  shouldSubmitIncubatorComposer,
} from "./incubator-chat-support";

test("incubator chat support builds draft transcript from first user message onward", () => {
  const messages = [
    ...createIncubatorInitialMessages(),
    createIncubatorMessage("user", "我想写一个修仙故事"),
    createIncubatorMessage("assistant", "可以先做成宗门成长线。"),
    createIncubatorMessage("user", "主角想替家族翻案"),
  ];

  assert.equal(
    buildIncubatorConversationText(messages),
    [
      "用户：我想写一个修仙故事",
      "助手：可以先做成宗门成长线。",
      "用户：主角想替家族翻案",
    ].join("\n\n"),
  );
});

test("incubator chat support builds stable fingerprints and model overrides", () => {
  const messages = [
    ...createIncubatorInitialMessages(),
    createIncubatorMessage("user", "给我三个方向"),
  ];

  assert.equal(
    buildIncubatorConversationFingerprint(messages, {
      modelName: "",
      provider: INCUBATOR_DEFAULT_PROVIDER,
    }),
    JSON.stringify({
      conversationText: "用户：给我三个方向",
      modelName: "",
      provider: INCUBATOR_DEFAULT_PROVIDER,
    }),
  );
  assert.equal(
    buildAssistantModelOverride({
      maxOutputTokens: "4096",
      modelName: "",
      provider: INCUBATOR_DEFAULT_PROVIDER,
    }),
    undefined,
  );
  assert.deepEqual(
    buildAssistantModelOverride({
      maxOutputTokens: "4096",
      modelName: "",
      provider: "openai",
    }),
    { max_tokens: 4096, name: undefined, provider: "openai" },
  );
  assert.deepEqual(
    buildAssistantModelOverride({
      maxOutputTokens: "8192",
      modelName: "gpt-4.1",
      provider: "openai",
    }),
    { max_tokens: 8192, name: "gpt-4.1", provider: "openai" },
  );
  assert.equal(resolveChatOutputModeLabel(true), "边写边显示");
  assert.equal(resolveChatOutputModeLabel(false), "生成后整体显示");
});

test("incubator chat support suggests project names from available setting signals", () => {
  assert.equal(
    buildSuggestedProjectName({
      genre: "玄幻",
      protagonist: { name: "林昭" },
    }),
    "林昭的玄幻故事",
  );
  assert.equal(
    buildSuggestedProjectName({
      protagonist: { identity: "宗门弃徒" },
    }),
    "宗门弃徒成长记",
  );
  assert.equal(buildSuggestedProjectName({}), "未命名新故事");
});

test("incubator chat support only shows suggestions before the first user message", () => {
  assert.equal(shouldShowPromptSuggestions(false), true);
  assert.equal(shouldShowPromptSuggestions(true), false);
});

test("incubator chat support uses Enter to submit and keeps Shift+Enter for newline", () => {
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: false, key: "Enter", shiftKey: false }),
    true,
  );
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: false, key: "Enter", shiftKey: true }),
    false,
  );
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: true, key: "Enter", shiftKey: false }),
    false,
  );
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: false, key: "a", shiftKey: false }),
    false,
  );
});

test("incubator chat support turns retired model replies into error guidance", () => {
  assert.deepEqual(
    resolveIncubatorAssistantReply(
      "Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro in the latest version of Antigravity.",
    ),
    {
      content: "当前默认模型已不可用，请换成可用模型后再试。上游提示：Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro in the latest version of Antigravity. 你可以先到“模型连接”里修改默认模型，再回来继续聊天。",
      status: "error",
    },
  );
});

test("incubator chat support replaces pending placeholder with streamed chunks", () => {
  const pendingMessage = createIncubatorMessage("assistant", INCUBATOR_PENDING_REPLY_MESSAGE, {
    status: "pending",
  });
  const firstChunk = appendIncubatorMessageDelta([pendingMessage], pendingMessage.id, "先给你三个方向");
  const secondChunk = appendIncubatorMessageDelta(firstChunk, pendingMessage.id, "，每个都能直接展开。");

  assert.equal(firstChunk[0]?.content, "先给你三个方向");
  assert.equal(secondChunk[0]?.content, "先给你三个方向，每个都能直接展开。");
});

test("incubator chat support keeps partial reply when streaming is interrupted", () => {
  assert.equal(resolveInterruptedIncubatorReply(INCUBATOR_PENDING_REPLY_MESSAGE), null);
  assert.equal(
    resolveInterruptedIncubatorReply("先给你两个方向"),
    `先给你两个方向\n\n${INCUBATOR_INTERRUPTED_REPLY_MESSAGE}`,
  );
});
