import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantPreferencesPayload,
  buildAssistantPreferencesFormKey,
  buildAssistantProviderOptions,
  isAssistantPreferencesDirty,
  toAssistantPreferencesDraft,
} from "./assistant-preferences-support";

test("assistant preferences support maps api data to editable draft", () => {
  assert.deepEqual(
    toAssistantPreferencesDraft({
      default_max_output_tokens: null,
      default_model_name: "gpt-4o-mini",
      default_provider: "openai",
    }),
    {
      defaultModelName: "gpt-4o-mini",
      defaultMaxOutputTokens: "",
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

test("assistant preferences support marks nullable token drafts and project scope options correctly", () => {
  const options = buildAssistantProviderOptions(
    [
      {
        id: "p1",
        owner_type: "project",
        provider: "anthropic",
        display_name: "项目 Anthropic",
        default_model: "claude-3-7-sonnet",
        is_active: true,
      },
      {
        id: "u1",
        owner_type: "user",
        provider: "openai",
        display_name: "个人 OpenAI",
        default_model: "gpt-4.1-mini",
        is_active: true,
      },
    ] as never,
    "project",
  );

  assert.deepEqual(options[0], {
    description: "不单独指定这个项目的连接，继续跟随个人 AI 偏好。",
    label: "跟随个人 AI 偏好",
    value: "",
  });
  assert.equal(options[1].description, "个人连接 · openai · 默认模型：gpt-4.1-mini");
  assert.equal(options[2].description, "项目连接 · anthropic · 默认模型：claude-3-7-sonnet");
  assert.equal(
    isAssistantPreferencesDirty(
      {
        defaultModelName: "",
        defaultMaxOutputTokens: "",
        defaultProvider: "",
      },
      {
        default_max_output_tokens: null,
        default_model_name: null,
        default_provider: null,
      },
    ),
    false,
  );
  assert.equal(
    buildAssistantPreferencesFormKey({
      default_max_output_tokens: null,
      default_model_name: null,
      default_provider: null,
    }),
    "none:none:none",
  );
});
