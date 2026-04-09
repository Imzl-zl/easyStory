import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIncubatorCredentialNotice,
  buildIncubatorCredentialOptions,
  pickIncubatorCredentialOption,
  resolveSelectedIncubatorCredentialOption,
  resolveHydratedIncubatorChatSettings,
  resolveIncubatorCredentialState,
} from "@/features/shared/assistant/assistant-credential-support";

test("incubator chat credential support keeps only active unique providers", () => {
  const options = buildIncubatorCredentialOptions([
    {
      api_dialect: "openai_responses",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: null,
      context_window_tokens: null,
      default_max_output_tokens: null,
      default_model: "gpt-4.1-mini",
      display_name: "OpenAI 主账号",
      extra_headers: null,
      user_agent_override: null,
      client_name: null,
      client_version: null,
      runtime_kind: null,
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
      context_window_tokens: null,
      default_max_output_tokens: null,
      default_model: "gpt-4.1",
      display_name: "OpenAI 备用",
      extra_headers: null,
      user_agent_override: null,
      client_name: null,
      client_version: null,
      runtime_kind: null,
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
      context_window_tokens: null,
      default_max_output_tokens: null,
      default_model: "gemini-2.5-flash",
      display_name: "Gemini",
      extra_headers: null,
      user_agent_override: null,
      client_name: null,
      client_version: null,
      runtime_kind: null,
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
      apiDialect: "openai_responses",
      baseUrl: null,
      bufferedToolVerifiedProbeKind: null,
      defaultModel: "gpt-4.1-mini",
      defaultMaxOutputTokens: null,
      displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
      provider: "openai",
      streamToolVerifiedProbeKind: null,
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
      apiDialect: "openai_responses",
      baseUrl: null,
      bufferedToolVerifiedProbeKind: null,
      defaultModel: "gpt-4.1-mini",
      defaultMaxOutputTokens: null,
      displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
      provider: "openai",
      streamToolVerifiedProbeKind: null,
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
      { maxOutputTokens: "", modelName: "", provider: "", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "openai_responses",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "gpt-4.1-mini",
        defaultMaxOutputTokens: null,
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
        streamToolVerifiedProbeKind: null,
      },
    ),
    {
      maxOutputTokens: "4096",
      modelName: "gpt-4.1-mini",
      provider: "openai",
      reasoningEffort: "",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );

  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "", modelName: "old-model", provider: "legacy-provider", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "openai_responses",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "gpt-4.1-mini",
        defaultMaxOutputTokens: null,
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
        streamToolVerifiedProbeKind: null,
      },
    ),
    {
      maxOutputTokens: "4096",
      modelName: "gpt-4.1-mini",
      provider: "openai",
      reasoningEffort: "",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );

  assert.equal(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "4096", modelName: "gpt-4.1", provider: "openai", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "openai_responses",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "gpt-4.1-mini",
        defaultMaxOutputTokens: null,
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
        streamToolVerifiedProbeKind: null,
      },
    ),
    null,
  );
});

test("incubator chat credential support prefers saved assistant preference before fallback", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "", modelName: "", provider: "", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "anthropic_messages",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "claude-3-7-sonnet",
        defaultMaxOutputTokens: 12288,
        displayLabel: "Anthropic · claude-3-7-sonnet",
        provider: "anthropic",
        streamToolVerifiedProbeKind: null,
      },
      {
        default_max_output_tokens: 8192,
        default_model_name: "claude-sonnet-4",
        default_provider: "anthropic",
        default_reasoning_effort: null,
        default_thinking_budget: null,
        default_thinking_level: null,
      },
    ),
    {
      maxOutputTokens: "8192",
      modelName: "claude-sonnet-4",
      provider: "anthropic",
      reasoningEffort: "",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
});

test("incubator chat credential support applies provider-agnostic model and reasoning defaults", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "", modelName: "", provider: "", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "openai_responses",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "gpt-4.1-mini",
        defaultMaxOutputTokens: 8192,
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
        streamToolVerifiedProbeKind: null,
      },
      {
        default_max_output_tokens: 4096,
        default_model_name: "gpt-5.4",
        default_provider: null,
        default_reasoning_effort: "high",
        default_thinking_budget: null,
        default_thinking_level: null,
      },
    ),
    {
      maxOutputTokens: "4096",
      modelName: "gpt-5.4",
      provider: "openai",
      reasoningEffort: "high",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
});

test("incubator chat credential support does not apply provider-agnostic openai defaults onto anthropic credentials", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "", modelName: "", provider: "", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "anthropic_messages",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "claude-sonnet-4",
        defaultMaxOutputTokens: 8192,
        displayLabel: "Anthropic · claude-sonnet-4",
        provider: "anthropic",
        streamToolVerifiedProbeKind: null,
      },
      {
        default_max_output_tokens: 4096,
        default_model_name: "gpt-5.4",
        default_provider: null,
        default_reasoning_effort: "high",
        default_thinking_budget: null,
        default_thinking_level: null,
      },
    ),
    {
      maxOutputTokens: "4096",
      modelName: "claude-sonnet-4",
      provider: "anthropic",
      reasoningEffort: "",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
});

test("incubator chat credential support keeps provider-agnostic custom openai-compatible models flexible", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "", modelName: "", provider: "", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "openai_chat_completions",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "gpt-4.1-mini",
        defaultMaxOutputTokens: 8192,
        displayLabel: "OpenAI 兼容 · gpt-4.1-mini",
        provider: "new_api",
        streamToolVerifiedProbeKind: null,
      },
      {
        default_max_output_tokens: 4096,
        default_model_name: "deepseek-reasoner",
        default_provider: null,
        default_reasoning_effort: "high",
        default_thinking_budget: null,
        default_thinking_level: null,
      },
    ),
    {
      maxOutputTokens: "4096",
      modelName: "deepseek-reasoner",
      provider: "new_api",
      reasoningEffort: "high",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
});

test("incubator chat credential support keeps gemini connections on stream output by default", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "", modelName: "", provider: "", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "gemini_generate_content",
        baseUrl: "https://x666.me",
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "gemini-2.5-flash",
        defaultMaxOutputTokens: null,
        displayLabel: "薄荷codex · gemini-2.5-flash",
        provider: "薄荷",
        streamToolVerifiedProbeKind: null,
      },
    ),
    {
      maxOutputTokens: "4096",
      modelName: "gemini-2.5-flash",
      provider: "薄荷",
      reasoningEffort: "",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
});

test("incubator chat credential support prefers safer connections before insecure public http", () => {
  const options = buildIncubatorCredentialOptions([
    {
      api_dialect: "openai_chat_completions",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: "http://49.234.21.84:3000",
      context_window_tokens: null,
      default_max_output_tokens: null,
      default_model: "gpt-5.2",
      display_name: "my_new",
      extra_headers: null,
      user_agent_override: null,
      client_name: null,
      client_version: null,
      runtime_kind: null,
      id: "1",
      is_active: true,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "new_api",
    },
    {
      api_dialect: "gemini_generate_content",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: "https://x666.me",
      context_window_tokens: null,
      default_max_output_tokens: null,
      default_model: "gemini-2.5-flash",
      display_name: "薄荷codex",
      extra_headers: null,
      user_agent_override: null,
      client_name: null,
      client_version: null,
      runtime_kind: null,
      id: "2",
      is_active: true,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "薄荷",
    },
  ]);

  assert.deepEqual(options.map((option) => option.provider), ["薄荷", "new_api"]);
  assert.equal(pickIncubatorCredentialOption(options, "")?.provider, "薄荷");
});

test("incubator chat credential support replaces blocked public http default for empty chats", () => {
  const options = [
    {
      apiDialect: "openai_chat_completions",
      baseUrl: "http://49.234.21.84:3000",
      bufferedToolVerifiedProbeKind: null,
      defaultModel: "gpt-5.2",
      defaultMaxOutputTokens: null,
      displayLabel: "my_new · gpt-5.2",
      provider: "new_api",
      streamToolVerifiedProbeKind: null,
    },
    {
      apiDialect: "gemini_generate_content",
      baseUrl: "https://x666.me",
      bufferedToolVerifiedProbeKind: null,
      defaultModel: "gemini-2.5-flash",
      defaultMaxOutputTokens: null,
      displayLabel: "薄荷codex · gemini-2.5-flash",
      provider: "薄荷",
      streamToolVerifiedProbeKind: null,
    },
  ];

  assert.equal(
    resolveSelectedIncubatorCredentialOption({
      currentProvider: "new_api",
      hasUserMessage: false,
      options,
      preferredProvider: "",
    })?.provider,
    "薄荷",
  );
  assert.equal(
    resolveSelectedIncubatorCredentialOption({
      currentProvider: "new_api",
      hasUserMessage: true,
      options,
      preferredProvider: "",
    })?.provider,
    "new_api",
  );
});

test("incubator chat credential support falls back to credential token limit when no assistant preference is set", () => {
  assert.deepEqual(
    resolveHydratedIncubatorChatSettings(
      { maxOutputTokens: "", modelName: "", provider: "", reasoningEffort: "", streamOutput: true, thinkingBudget: "", thinkingLevel: "" },
      {
        apiDialect: "openai_responses",
        baseUrl: null,
        bufferedToolVerifiedProbeKind: null,
        defaultModel: "gpt-4.1-mini",
        defaultMaxOutputTokens: 16384,
        displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
        provider: "openai",
        streamToolVerifiedProbeKind: null,
      },
    ),
    {
      maxOutputTokens: "16384",
      modelName: "gpt-4.1-mini",
      provider: "openai",
      reasoningEffort: "",
      streamOutput: true,
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
});
