import assert from "node:assert/strict";
import test from "node:test";

import { resolveAssistantReasoningControl } from "@/features/shared/assistant/assistant-reasoning-support";

import {
  buildAssistantPreferencesPayload,
  buildAssistantPreferencesFormKey,
  buildAssistantProviderOptions,
  isAssistantPreferencesDirty,
  normalizeAssistantPreferencesDraft,
  toAssistantPreferencesDraft,
} from "@/features/settings/components/assistant/preferences/assistant-preferences-support";

test("assistant preferences support maps api data to editable draft", () => {
  assert.deepEqual(
    toAssistantPreferencesDraft({
      default_max_output_tokens: null,
      default_model_name: "gpt-4o-mini",
      default_provider: "openai",
      default_reasoning_effort: "high",
      default_thinking_budget: null,
      default_thinking_level: null,
    }),
    {
      defaultModelName: "gpt-4o-mini",
      defaultMaxOutputTokens: "",
      defaultProvider: "openai",
      defaultReasoningEffort: "high",
      defaultThinkingBudget: "",
      defaultThinkingLevel: "",
    },
  );
});

test("assistant preferences support builds normalized payloads and dirty checks", () => {
  const anthropicControl = resolveAssistantReasoningControl({ apiDialect: "anthropic_messages" });
  const draft = {
    defaultModelName: " claude-sonnet-4 ",
    defaultMaxOutputTokens: " 8192 ",
    defaultProvider: " anthropic ",
    defaultReasoningEffort: "",
    defaultThinkingBudget: "",
    defaultThinkingLevel: "",
  };
  const payload = buildAssistantPreferencesPayload(draft, anthropicControl);
  assert.deepEqual(payload, {
    default_model_name: "claude-sonnet-4",
    default_max_output_tokens: 8192,
    default_provider: "anthropic",
    default_reasoning_effort: null,
    default_thinking_budget: null,
    default_thinking_level: null,
  });
  assert.equal(
    isAssistantPreferencesDirty(draft, {
      default_max_output_tokens: 8192,
      default_model_name: "claude-sonnet-4",
      default_provider: "anthropic",
      default_reasoning_effort: null,
      default_thinking_budget: null,
      default_thinking_level: null,
    }, anthropicControl),
    false,
  );
});

test("assistant preferences support builds provider options from active connections", () => {
  assert.deepEqual(
    buildAssistantProviderOptions([
      { id: "1", api_dialect: "openai_responses", provider: "openai", display_name: "OpenAI", is_active: true },
      { id: "2", api_dialect: "anthropic_messages", provider: "anthropic", display_name: "Anthropic", is_active: true },
      { id: "3", api_dialect: "openai_responses", provider: "openai", display_name: "OpenAI 2", is_active: true },
      { id: "4", api_dialect: "gemini_generate_content", provider: "gemini", display_name: "Gemini", is_active: false },
    ] as never),
    [
      {
        description: "不固定到某条连接，聊天时按系统默认方式处理。",
        label: "跟随系统默认",
        value: "",
      },
      {
        apiDialect: "anthropic_messages",
        description: "已启用连接 · anthropic",
        label: "Anthropic",
        value: "anthropic",
      },
      {
        apiDialect: "openai_responses",
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
        api_dialect: "anthropic_messages",
        id: "p1",
        owner_type: "project",
        provider: "anthropic",
        display_name: "项目 Anthropic",
        default_model: "claude-3-7-sonnet",
        is_active: true,
      },
      {
        api_dialect: "openai_responses",
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
  assert.equal(options[1].defaultModel, "gpt-4.1-mini");
  assert.equal(options[1].description, "个人连接 · openai · 默认模型：gpt-4.1-mini");
  assert.equal(options[2].description, "项目连接 · anthropic · 默认模型：claude-3-7-sonnet");
  assert.equal(
    isAssistantPreferencesDirty(
      {
        defaultModelName: "",
        defaultMaxOutputTokens: "",
        defaultProvider: "",
        defaultReasoningEffort: "",
        defaultThinkingBudget: "",
        defaultThinkingLevel: "",
      },
      {
        default_max_output_tokens: null,
        default_model_name: null,
        default_provider: null,
        default_reasoning_effort: null,
        default_thinking_budget: null,
        default_thinking_level: null,
      },
      resolveAssistantReasoningControl({ apiDialect: null }),
    ),
    false,
  );
  assert.equal(
    buildAssistantPreferencesFormKey({
      default_max_output_tokens: null,
      default_model_name: null,
      default_provider: null,
      default_reasoning_effort: null,
      default_thinking_budget: null,
      default_thinking_level: null,
    }),
    "none:none:none:none:none:none",
  );
});

test("assistant preferences support keeps openai reasoning visible for flexible model choices", () => {
  const preferences = {
    default_max_output_tokens: null,
    default_model_name: "gpt-4.1",
    default_provider: null,
    default_reasoning_effort: "high",
    default_thinking_budget: null,
    default_thinking_level: null,
  } as const;
  const reasoningControl = resolveAssistantReasoningControl({
    modelName: "gpt-4.1",
  });
  const draft = toAssistantPreferencesDraft(preferences);

  assert.equal(reasoningControl.kind, "openai");
  assert.equal(isAssistantPreferencesDirty(draft, preferences, reasoningControl), false);
  assert.deepEqual(
    buildAssistantPreferencesPayload(
      normalizeAssistantPreferencesDraft(draft, reasoningControl),
      reasoningControl,
    ),
    {
      default_model_name: "gpt-4.1",
      default_max_output_tokens: null,
      default_provider: null,
      default_reasoning_effort: "high",
      default_thinking_budget: null,
      default_thinking_level: null,
    },
  );
});

test("assistant preferences support preserves legacy conflicting reasoning fields instead of normalizing them away", () => {
  const preferences = {
    default_max_output_tokens: null,
    default_model_name: "gpt-5.4",
    default_provider: null,
    default_reasoning_effort: "high",
    default_thinking_budget: null,
    default_thinking_level: "low",
  } as const;
  const reasoningControl = resolveAssistantReasoningControl({
    modelName: "gpt-5.4",
  });
  const draft = toAssistantPreferencesDraft(preferences);

  assert.deepEqual(
    normalizeAssistantPreferencesDraft(draft, reasoningControl),
    draft,
  );
  assert.equal(isAssistantPreferencesDirty(draft, preferences, reasoningControl), false);
  assert.deepEqual(
    buildAssistantPreferencesPayload(draft, reasoningControl),
    {
      default_model_name: "gpt-5.4",
      default_max_output_tokens: null,
      default_provider: null,
      default_reasoning_effort: "high",
      default_thinking_budget: null,
      default_thinking_level: "low",
    },
  );
});
