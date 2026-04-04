import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";
import {
  buildCredentialCreatePayload,
  buildCredentialUpdatePayload,
  createCredentialFormFromView,
  isCredentialFormDirty,
  normalizeOptionalQueryValue,
  resolveCredentialEditorState,
} from "./credential-center-support";

test("createCredentialFormFromView rehydrates default base url when credential uses official default", () => {
  const form = createCredentialFormFromView(createCredential({ base_url: null }));
  assert.equal(form.baseUrl, "https://api.openai.com");
  assert.equal(form.apiKey, "");
});

test("buildCredentialCreatePayload maps project scope and trims default base url to null", () => {
  const payload = buildCredentialCreatePayload({
    formState: {
      apiDialect: "openai_chat_completions",
      apiKey: "secret-key",
      baseUrl: "https://api.openai.com",
      defaultModel: " gpt-4o-mini ",
      contextWindowTokens: "128000",
      defaultMaxOutputTokens: "8192",
      displayName: " My OpenAI ",
      authStrategy: "",
      apiKeyHeaderName: "",
      extraHeadersText: "",
      userAgentOverride: "",
      clientName: "",
      clientVersion: "",
      runtimeKind: "",
      provider: " OpenAI ",
    },
    projectId: "project-1",
    scope: "project",
  });
  assert.deepEqual(payload, {
    owner_type: "project",
    project_id: "project-1",
    provider: "OpenAI",
    api_dialect: "openai_chat_completions",
    display_name: "My OpenAI",
    api_key: "secret-key",
    base_url: null,
    default_model: "gpt-4o-mini",
    context_window_tokens: 128000,
    default_max_output_tokens: 8192,
    auth_strategy: null,
    api_key_header_name: null,
    extra_headers: null,
    user_agent_override: null,
    client_name: null,
    client_version: null,
    runtime_kind: null,
  });
});

test("buildCredentialUpdatePayload only sends changed fields and rotates key when provided", () => {
  const payload = buildCredentialUpdatePayload(createCredential(), {
    apiDialect: "anthropic_messages",
    apiKey: "rotated-key",
    baseUrl: "https://proxy.example.com",
    defaultModel: "claude-sonnet-4-20250514",
    contextWindowTokens: "200000",
    defaultMaxOutputTokens: "12288",
    displayName: "Anthropic Proxy",
    authStrategy: "custom_header",
    apiKeyHeaderName: "api-key",
    extraHeadersText: '{ "X-Trace-Id": "trace-001" }',
    userAgentOverride: " codex-cli/0.118.0 (server; node) ",
    clientName: " easyStory ",
    clientVersion: " 0.1 ",
    runtimeKind: "server-python",
    provider: "openai",
  });
  assert.deepEqual(payload, {
    api_dialect: "anthropic_messages",
    api_key: "rotated-key",
    base_url: "https://proxy.example.com",
    default_model: "claude-sonnet-4-20250514",
    context_window_tokens: 200000,
    default_max_output_tokens: 12288,
    display_name: "Anthropic Proxy",
    auth_strategy: "custom_header",
    api_key_header_name: "api-key",
    extra_headers: { "X-Trace-Id": "trace-001" },
    user_agent_override: "codex-cli/0.118.0 (server; node)",
    client_name: "easyStory",
    client_version: "0.1",
    runtime_kind: "server-python",
  });
});

test("buildCredentialUpdatePayload can clear custom base url without sending unchanged blanks", () => {
  const payload = buildCredentialUpdatePayload(
    createCredential({ base_url: "https://proxy.example.com" }),
    {
      apiDialect: "openai_chat_completions",
      apiKey: "",
      baseUrl: "https://api.openai.com",
      defaultModel: "gpt-4o-mini",
      contextWindowTokens: "",
      defaultMaxOutputTokens: "",
      displayName: "OpenAI",
      authStrategy: "",
      apiKeyHeaderName: "",
      extraHeadersText: "",
      userAgentOverride: "",
      clientName: "",
      clientVersion: "",
      runtimeKind: "",
      provider: "openai",
    },
  );
  assert.deepEqual(payload, {
    base_url: null,
  });
});

test("buildCredentialUpdatePayload rejects clearing an existing default model", () => {
  assert.throws(
    () =>
      buildCredentialUpdatePayload(createCredential(), {
        apiDialect: "openai_chat_completions",
        apiKey: "",
        baseUrl: "https://api.openai.com",
        defaultModel: "   ",
        contextWindowTokens: "",
        defaultMaxOutputTokens: "",
        displayName: "OpenAI",
        authStrategy: "",
        apiKeyHeaderName: "",
        extraHeadersText: "",
        userAgentOverride: "",
        clientName: "",
        clientVersion: "",
        runtimeKind: "",
        provider: "openai",
      }),
    /不支持清空默认模型/,
  );
});

test("buildCredentialCreatePayload parses extra headers json and keeps custom header auth", () => {
  const payload = buildCredentialCreatePayload({
    formState: {
      apiDialect: "openai_chat_completions",
      apiKey: "secret-key",
      baseUrl: "https://proxy.example.com",
      defaultModel: "gpt-4o-mini",
      contextWindowTokens: "",
      defaultMaxOutputTokens: "",
      displayName: "OpenAI Proxy",
      authStrategy: "custom_header",
      apiKeyHeaderName: "api-key",
      extraHeadersText: '{ "X-Trace-Id": "trace-009" }',
      userAgentOverride: "",
      clientName: "",
      clientVersion: "",
      runtimeKind: "",
      provider: "proxy",
    },
    projectId: null,
    scope: "user",
  });
  assert.equal(payload.auth_strategy, "custom_header");
  assert.equal(payload.api_key_header_name, "api-key");
  assert.deepEqual(payload.extra_headers, { "X-Trace-Id": "trace-009" });
});

test("buildCredentialCreatePayload rejects invalid extra headers json", () => {
  assert.throws(
    () =>
      buildCredentialCreatePayload({
        formState: {
          apiDialect: "openai_chat_completions",
          apiKey: "secret-key",
          baseUrl: "https://api.openai.com",
          defaultModel: "gpt-4o-mini",
          contextWindowTokens: "",
          defaultMaxOutputTokens: "",
          displayName: "OpenAI",
          authStrategy: "",
          apiKeyHeaderName: "",
          extraHeadersText: '["bad"]',
          userAgentOverride: "",
          clientName: "",
          clientVersion: "",
          runtimeKind: "",
          provider: "openai",
        },
        projectId: null,
        scope: "user",
      }),
    /JSON 对象/,
  );
});

test("buildCredentialCreatePayload rejects client identity without client name", () => {
  assert.throws(
    () =>
      buildCredentialCreatePayload({
        formState: {
          apiDialect: "openai_chat_completions",
          apiKey: "secret-key",
          baseUrl: "https://api.openai.com",
          defaultModel: "gpt-4o-mini",
          contextWindowTokens: "",
          defaultMaxOutputTokens: "",
          displayName: "OpenAI",
          authStrategy: "",
          apiKeyHeaderName: "",
          extraHeadersText: "",
          userAgentOverride: "",
          clientName: "",
          clientVersion: "0.1",
          runtimeKind: "",
          provider: "openai",
        },
        projectId: null,
        scope: "user",
      }),
    /必须先填写应用名/,
  );
});

test("buildCredentialCreatePayload rejects runtime-managed auth header names", () => {
  assert.throws(
    () =>
      buildCredentialCreatePayload({
        formState: {
          apiDialect: "anthropic_messages",
          apiKey: "secret-key",
          baseUrl: "https://proxy.example.com",
          defaultModel: "claude-haiku",
          contextWindowTokens: "",
          defaultMaxOutputTokens: "",
          displayName: "Anthropic Proxy",
          authStrategy: "custom_header",
          apiKeyHeaderName: "anthropic-version",
          extraHeadersText: "",
          userAgentOverride: "",
          clientName: "",
          clientVersion: "",
          runtimeKind: "",
          provider: "proxy",
        },
        projectId: null,
        scope: "user",
      }),
    /不能覆盖系统托管的请求头/,
  );
});

test("buildCredentialCreatePayload rejects sensitive extra headers even when auth follows dialect default", () => {
  assert.throws(
    () =>
      buildCredentialCreatePayload({
        formState: {
          apiDialect: "openai_chat_completions",
          apiKey: "secret-key",
          baseUrl: "https://proxy.example.com",
          defaultModel: "gpt-4o-mini",
          contextWindowTokens: "",
          defaultMaxOutputTokens: "",
          displayName: "OpenAI Proxy",
          authStrategy: "",
          apiKeyHeaderName: "",
          extraHeadersText: '{ "Authorization": "Bearer should-not-be-here" }',
          userAgentOverride: "",
          clientName: "",
          clientVersion: "",
          runtimeKind: "",
          provider: "proxy",
        },
        projectId: null,
        scope: "user",
      }),
    /鉴权或敏感信息/,
  );
});

test("normalizeOptionalQueryValue trims blank query params to null", () => {
  assert.equal(normalizeOptionalQueryValue(" credential-1 "), "credential-1");
  assert.equal(normalizeOptionalQueryValue("   "), null);
  assert.equal(normalizeOptionalQueryValue(null), null);
});

test("isCredentialFormDirty compares current form against initial state", () => {
  const initialState = createCredentialFormFromView(createCredential());
  assert.equal(isCredentialFormDirty(initialState, initialState), false);
  assert.equal(
    isCredentialFormDirty({ ...initialState, displayName: "新的名称" }, initialState),
    true,
  );
  assert.equal(
    isCredentialFormDirty({ ...initialState, apiKey: "rotated-key" }, initialState),
    true,
  );
});

test("isCredentialFormDirty ignores edit changes that normalize back to the same payload", () => {
  const credential = createCredential({ display_name: "lucky" });
  const initialState = createCredentialFormFromView(credential);

  assert.equal(
    isCredentialFormDirty({ ...initialState, displayName: " lucky " }, initialState, credential),
    false,
  );
  assert.equal(
    isCredentialFormDirty({ ...initialState, displayName: "lucky 2" }, initialState, credential),
    true,
  );
});

test("resolveCredentialEditorState prefers saved snapshot for edit baseline and bumps form key", () => {
  const staleCredential = createCredential({ display_name: "旧名称" });
  const savedCredential = createCredential({ display_name: "新名称" });

  const result = resolveCredentialEditorState({
    createFormVersion: 0,
    editFormVersion: 3,
    editableCredential: staleCredential,
    savedEditableCredential: savedCredential,
    scope: "user",
    scopedProjectId: null,
  });

  assert.equal(result.activeFormKey, "edit:credential-1:3");
  assert.equal(result.activeInitialState.displayName, "新名称");
  assert.equal(result.activeInitialState.apiKey, "");
});

test("resolveCredentialEditorState builds create baseline when nothing is being edited", () => {
  const result = resolveCredentialEditorState({
    createFormVersion: 2,
    editFormVersion: 0,
    editableCredential: null,
    savedEditableCredential: createCredential(),
    scope: "project",
    scopedProjectId: "project-1",
  });

  assert.equal(result.activeFormKey, "create:project:project-1:2");
  assert.equal(result.activeInitialState.displayName, "");
  assert.equal(result.activeInitialState.apiKey, "");
});

test("buildCredentialUpdatePayload can clear client identity fields", () => {
  const payload = buildCredentialUpdatePayload(
    createCredential({
      client_name: "easyStory",
      client_version: "0.1",
      runtime_kind: "server-python",
    }),
    {
      ...createCredentialFormFromView(
        createCredential({
          client_name: "easyStory",
          client_version: "0.1",
          runtime_kind: "server-python",
        }),
      ),
      clientName: "",
      clientVersion: "",
      runtimeKind: "",
    },
  );
  assert.deepEqual(payload, {
    client_name: null,
    client_version: null,
    runtime_kind: null,
  });
});

test("buildCredentialUpdatePayload can clear user agent override", () => {
  const payload = buildCredentialUpdatePayload(
    createCredential({ user_agent_override: "codex-cli/0.118.0 (server; node)" }),
    {
      ...createCredentialFormFromView(
        createCredential({ user_agent_override: "codex-cli/0.118.0 (server; node)" }),
      ),
      userAgentOverride: "",
    },
  );
  assert.deepEqual(payload, {
    user_agent_override: null,
  });
});

function createCredential(overrides: Partial<CredentialView> = {}): CredentialView {
  return {
    id: "credential-1",
    owner_type: "user",
    owner_id: "user-1",
    provider: "openai",
    api_dialect: "openai_chat_completions",
    display_name: "OpenAI",
    masked_key: "sk-...1234",
    base_url: null,
    default_model: "gpt-4o-mini",
    context_window_tokens: null,
    default_max_output_tokens: null,
    auth_strategy: null,
    api_key_header_name: null,
    extra_headers: null,
    user_agent_override: null,
    client_name: null,
    client_version: null,
    runtime_kind: null,
    is_active: true,
    last_verified_at: null,
    ...overrides,
  };
}
