import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantModelOverride,
  buildIncubatorConversationFingerprint,
  buildIncubatorConversationText,
  buildSuggestedProjectName,
  createIncubatorInitialMessages,
  createIncubatorMessage,
  INCUBATOR_DEFAULT_PROVIDER,
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
      modelName: "",
      provider: INCUBATOR_DEFAULT_PROVIDER,
    }),
    undefined,
  );
  assert.deepEqual(
    buildAssistantModelOverride({
      modelName: "",
      provider: "openai",
    }),
    { name: undefined, provider: "openai" },
  );
  assert.deepEqual(
    buildAssistantModelOverride({
      modelName: "gpt-4.1",
      provider: "openai",
    }),
    { name: "gpt-4.1", provider: "openai" },
  );
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
