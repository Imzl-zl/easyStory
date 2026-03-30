import assert from "node:assert/strict";
import test from "node:test";

import {
  buildChatSettingsSummaryItems,
  normalizeMaxOutputTokensInput,
  syncProviderSelection,
} from "./incubator-chat-settings-support";

test("incubator chat settings support keeps token input numeric", () => {
  assert.equal(normalizeMaxOutputTokensInput(" 8a1-92 "), "8192");
});

test("incubator chat settings support keeps summary compact when using connection defaults", () => {
  const items = buildChatSettingsSummaryItems({
    credentialOptions: [{
      apiDialect: "openai_responses",
      defaultModel: "gpt-4.1",
      defaultMaxOutputTokens: 8192,
      displayLabel: "OpenAI 主账号 · gpt-4.1",
      provider: "openai",
    }],
    credentialState: "ready",
    settings: {
      agentId: "",
      allowSystemCredentialPool: false,
      hookIds: [],
      maxOutputTokens: "8192",
      modelName: "",
      provider: "openai",
      skillId: "skill.assistant.general_chat",
      streamOutput: true,
    },
  } as never);

  assert.deepEqual(items, ["OpenAI 主账号"]);
});

test("incubator chat settings support shows only changed summary items", () => {
  const items = buildChatSettingsSummaryItems({
    credentialOptions: [{
      apiDialect: "openai_responses",
      defaultModel: "gpt-4.1",
      defaultMaxOutputTokens: 8192,
      displayLabel: "OpenAI 主账号 · gpt-4.1",
      provider: "openai",
    }],
    credentialState: "ready",
    settings: {
      agentId: "",
      allowSystemCredentialPool: false,
      hookIds: [],
      maxOutputTokens: "12000",
      modelName: "gpt-4.1-mini",
      provider: "openai",
      skillId: "skill.assistant.general_chat",
      streamOutput: false,
    },
  } as never);

  assert.deepEqual(items, [
    "OpenAI 主账号",
    "gpt-4.1-mini",
    "上限 12000",
    "生成后整体显示",
  ]);
});

test("incubator chat settings support syncs token limit when switching to a new connection default", () => {
  const initialSettings = {
    agentId: "",
    allowSystemCredentialPool: false,
    hookIds: [],
    maxOutputTokens: "4096",
    modelName: "gpt-4.1",
    provider: "openai",
    skillId: "skill.assistant.general_chat",
    streamOutput: true,
  };
  let nextSettings: typeof initialSettings | null = null;
  const model = {
    credentialOptions: [
      {
        apiDialect: "openai_responses",
        defaultModel: "gpt-4.1",
        defaultMaxOutputTokens: 4096,
        displayLabel: "OpenAI 主账号 · gpt-4.1",
        provider: "openai",
      },
      {
        apiDialect: "anthropic_messages",
        defaultModel: "claude-sonnet-4",
        defaultMaxOutputTokens: 12288,
        displayLabel: "Claude · claude-sonnet-4",
        provider: "anthropic",
      },
    ],
    setSettings: (updater: (current: typeof initialSettings) => typeof initialSettings) => {
      nextSettings = updater(initialSettings);
    },
    settings: initialSettings,
  };

  syncProviderSelection(model as never, "anthropic");

  assert.deepEqual(nextSettings, {
    agentId: "",
    allowSystemCredentialPool: false,
    hookIds: [],
    maxOutputTokens: "12288",
    modelName: "claude-sonnet-4",
    provider: "anthropic",
    skillId: "skill.assistant.general_chat",
    streamOutput: true,
  });
});
