import assert from "node:assert/strict";
import test from "node:test";

import {
  buildChatSettingsSummaryItems,
  normalizeMaxOutputTokensInput,
  syncProviderSelection,
} from "@/features/lobby/components/incubator/incubator-chat-settings-support";

test("incubator chat settings support keeps token input numeric", () => {
  assert.equal(normalizeMaxOutputTokensInput(" 8a1-92 "), "8192");
});

test("incubator chat settings support keeps summary compact when using connection defaults", () => {
  const items = buildChatSettingsSummaryItems({
    credentialOptions: [{
      apiDialect: "openai_responses",
      defaultModel: "gpt-5.4",
      defaultMaxOutputTokens: 8192,
      displayLabel: "OpenAI 主账号 · gpt-5.4",
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
      reasoningEffort: "",
      skillId: "",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  } as never);

  assert.deepEqual(items, ["OpenAI 主账号"]);
});

test("incubator chat settings support shows only changed summary items", () => {
  const items = buildChatSettingsSummaryItems({
    credentialOptions: [{
      apiDialect: "openai_responses",
      defaultModel: "gpt-5.4",
      defaultMaxOutputTokens: 8192,
      displayLabel: "OpenAI 主账号 · gpt-5.4",
      provider: "openai",
    }],
    credentialState: "ready",
    settings: {
      agentId: "",
      allowSystemCredentialPool: false,
      hookIds: [],
      maxOutputTokens: "12000",
      modelName: "gpt-5.4",
      provider: "openai",
      reasoningEffort: "high",
      skillId: "",
      streamOutput: false,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  } as never);

  assert.deepEqual(items, [
    "OpenAI 主账号",
    "思考 高",
    "上限 12000",
    "生成后整体显示",
  ]);
});

test("incubator chat settings support keeps blank token limit when switching connection", () => {
  const initialSettings = {
    agentId: "",
    allowSystemCredentialPool: false,
    hookIds: [],
    maxOutputTokens: "",
    modelName: "gpt-5.4",
    provider: "openai",
    reasoningEffort: "high",
    skillId: "",
    streamOutput: true,
    thinkingBudget: "",
    thinkingLevel: "",
  };
  let nextSettings: typeof initialSettings | null = null;
  const model = {
    credentialOptions: [
      {
        apiDialect: "openai_responses",
        defaultModel: "gpt-5.4",
        defaultMaxOutputTokens: 4096,
        displayLabel: "OpenAI 主账号 · gpt-5.4",
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
    maxOutputTokens: "",
    modelName: "claude-sonnet-4",
    provider: "anthropic",
    reasoningEffort: "",
    skillId: "",
    streamOutput: true,
    thinkingBudget: "",
    thinkingLevel: "",
  });
});

test("incubator chat settings support keeps explicit token limit when switching connection", () => {
  const initialSettings = {
    agentId: "",
    allowSystemCredentialPool: false,
    hookIds: [],
    maxOutputTokens: "4096",
    modelName: "gpt-5.4",
    provider: "openai",
    reasoningEffort: "high",
    skillId: "",
    streamOutput: true,
    thinkingBudget: "",
    thinkingLevel: "",
  };
  let nextSettings: typeof initialSettings | null = null;
  const model = {
    credentialOptions: [
      {
        apiDialect: "openai_responses",
        defaultModel: "gpt-5.4",
        defaultMaxOutputTokens: 4096,
        displayLabel: "OpenAI 主账号 · gpt-5.4",
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
    maxOutputTokens: "4096",
    modelName: "claude-sonnet-4",
    provider: "anthropic",
    reasoningEffort: "",
    skillId: "",
    streamOutput: true,
    thinkingBudget: "",
    thinkingLevel: "",
  });
});
