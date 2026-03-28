import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIncubatorCredentialNotice,
  buildIncubatorCredentialOptions,
  pickIncubatorCredentialOption,
  resolveHydratedIncubatorChatSettings,
  resolveIncubatorCredentialState,
} from "./incubator-chat-credential-support";

test("incubator chat credential support keeps only active unique providers", () => {
  const options = buildIncubatorCredentialOptions([
    {
      api_dialect: "openai_responses",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: null,
      default_model: "gpt-4.1-mini",
      display_name: "OpenAI 主账号",
      extra_headers: null,
      id: "1",
      is_active: true,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "openai",
    },
    {
      api_dialect: "openai_responses",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: null,
      default_model: "gpt-4.1",
      display_name: "OpenAI 备用",
      extra_headers: null,
      id: "2",
      is_active: true,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "openai",
    },
    {
      api_dialect: "gemini_generate_content",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: null,
      default_model: "gemini-2.5-flash",
      display_name: "Gemini",
      extra_headers: null,
      id: "3",
      is_active: false,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "gemini",
    },
  ]);

  assert.deepEqual(options, [
    {
      defaultModel: "gpt-4.1-mini",
      displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
      provider: "openai",
    },
  ]);
  const selectedOption = pickIncubatorCredentialOption(options, "");
  assert.ok(selectedOption);
  assert.equal(selectedOption.provider, "openai");
});

test("incubator chat credential support builds setup notice when no credential exists", () => {
  assert.equal(buildIncubatorCredentialNotice({
    credentialOptions: [],
    errorMessage: null,
    isLoading: true,
  }), null);
  assert.equal(
    buildIncubatorCredentialNotice({
      credentialOptions: [],
      errorMessage: null,
      isLoading: false,
    }),
    "当前账号没有可用模型连接，请先启用。",
  );
});

test("incubator chat credential support distinguishes loading error empty and ready states", () => {
  assert.equal(resolveIncubatorCredentialState({
    credentialOptions: [],
    errorMessage: null,
    isLoading: true,
  }), "loading");
  assert.equal(resolveIncubatorCredentialState({
    credentialOptions: [],
    errorMessage: "network failed",
    isLoading: false,
  }), "error");
  assert.equal(resolveIncubatorCredentialState({
    credentialOptions: [],
    errorMessage: null,
    isLoading: false,
  }), "empty");
  assert.equal(resolveIncubatorCredentialState({
    credentialOptions: [{
      defaultModel: "gpt-4.1-mini",
      displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
      provider: "openai",
    }],
    errorMessage: null,
    isLoading: false,
  }), "ready");
});

test("incubator chat credential support builds readable notice for query failures", () => {
  assert.equal(
    buildIncubatorCredentialNotice({
      credentialOptions: [],
      errorMessage: "请求超时",
      isLoading: false,
    }),
    "模型连接读取失败，请刷新后重试。错误信息：请求超时",
  );
});

test("incubator chat credential support hydrates defaults after recovery and fixes stale provider", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { modelName: "", provider: "" },
      {
        defaultModel: "gpt-4.1-mini",
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
      },
    ),
    {
      modelName: "gpt-4.1-mini",
      provider: "openai",
    },
  );

  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { modelName: "old-model", provider: "legacy-provider" },
      {
        defaultModel: "gpt-4.1-mini",
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
      },
    ),
    {
      modelName: "gpt-4.1-mini",
      provider: "openai",
    },
  );

  assert.equal(
    resolveHydratedIncubatorChatSettings(
      { modelName: "gpt-4.1", provider: "openai" },
      {
        defaultModel: "gpt-4.1-mini",
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
      },
    ),
    null,
  );
});

test("incubator chat credential support prefers saved assistant preference before fallback", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { modelName: "", provider: "" },
      {
        defaultModel: "claude-3-7-sonnet",
        displayLabel: "Anthropic · claude-3-7-sonnet",
        provider: "anthropic",
      },
      {
        default_model_name: "claude-sonnet-4",
        default_provider: "anthropic",
      },
    ),
    {
      modelName: "claude-sonnet-4",
      provider: "anthropic",
    },
  );
});
