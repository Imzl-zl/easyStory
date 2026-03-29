import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantPreferencesPayload,
  buildAssistantProviderOptions,
  isAssistantPreferencesDirty,
  toAssistantPreferencesDraft,
} from "./assistant-preferences-support";

test("assistant preferences support maps api data to editable draft", () => {
  assert.deepEqual(
    toAssistantPreferencesDraft({
      default_max_output_tokens: 4096,
      default_model_name: "gpt-4o-mini",
      default_provider: "openai",
    }),
    {
      defaultModelName: "gpt-4o-mini",
      defaultMaxOutputTokens: "4096",
      defaultProvider: "openai",
    },
  );
});

test("assistant preferences support builds normalized payloads and dirty checks", () => {
  const draft = {
    defaultModelName: " claude-sonnet-4 ",
    defaultMaxOutputTokens: " 8192 ",
    defaultProvider: " anthropic ",
  };
  const payload = buildAssistantPreferencesPayload(draft);
  assert.deepEqual(payload, {
    default_model_name: "claude-sonnet-4",
    default_max_output_tokens: 8192,
    default_provider: "anthropic",
  });
  assert.equal(
    isAssistantPreferencesDirty(draft, {
      default_max_output_tokens: 8192,
      default_model_name: "claude-sonnet-4",
      default_provider: "anthropic",
    }),
    false,
  );
});

test("assistant preferences support builds provider options from active connections", () => {
  assert.deepEqual(
    buildAssistantProviderOptions([
      { id: "1", provider: "openai", display_name: "OpenAI", is_active: true },
      { id: "2", provider: "anthropic", display_name: "Anthropic", is_active: true },
      { id: "3", provider: "openai", display_name: "OpenAI 2", is_active: true },
      { id: "4", provider: "gemini", display_name: "Gemini", is_active: false },
    ] as never),
    [
      {
        description: "不固定到某条连接，聊天时按系统默认方式处理。",
        label: "跟随系统默认",
        value: "",
      },
      {
        description: "已启用连接 · anthropic",
        label: "Anthropic",
        value: "anthropic",
      },
      {
        description: "已启用连接 · openai",
        label: "OpenAI",
        value: "openai",
      },
    ],
  );
});
