import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";
import {
  buildCredentialCreatePayload,
  buildCredentialUpdatePayload,
  createCredentialFormFromView,
  isCredentialFormDirty,
  normalizeOptionalQueryValue,
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
      displayName: " My OpenAI ",
      authStrategy: "",
      apiKeyHeaderName: "",
      extraHeadersText: "",
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
    auth_strategy: null,
    api_key_header_name: null,
    extra_headers: null,
  });
});

test("buildCredentialUpdatePayload only sends changed fields and rotates key when provided", () => {
  const payload = buildCredentialUpdatePayload(createCredential(), {
    apiDialect: "anthropic_messages",
    apiKey: "rotated-key",
    baseUrl: "https://proxy.example.com",
    defaultModel: "claude-sonnet-4-20250514",
    displayName: "Anthropic Proxy",
    authStrategy: "custom_header",
    apiKeyHeaderName: "api-key",
    extraHeadersText: '{ "X-Trace-Id": "trace-001" }',
    provider: "openai",
  });
  assert.deepEqual(payload, {
    api_dialect: "anthropic_messages",
    api_key: "rotated-key",
    base_url: "https://proxy.example.com",
    default_model: "claude-sonnet-4-20250514",
    display_name: "Anthropic Proxy",
    auth_strategy: "custom_header",
    api_key_header_name: "api-key",
    extra_headers: { "X-Trace-Id": "trace-001" },
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
      displayName: "OpenAI",
      authStrategy: "",
      apiKeyHeaderName: "",
      extraHeadersText: "",
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
        displayName: "OpenAI",
        authStrategy: "",
        apiKeyHeaderName: "",
        extraHeadersText: "",
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
      displayName: "OpenAI Proxy",
      authStrategy: "custom_header",
      apiKeyHeaderName: "api-key",
      extraHeadersText: '{ "X-Trace-Id": "trace-009" }',
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
          displayName: "OpenAI",
          authStrategy: "",
          apiKeyHeaderName: "",
          extraHeadersText: '["bad"]',
          provider: "openai",
        },
        projectId: null,
        scope: "user",
      }),
    /JSON 对象/,
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
          displayName: "Anthropic Proxy",
          authStrategy: "custom_header",
          apiKeyHeaderName: "anthropic-version",
          extraHeadersText: "",
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
          displayName: "OpenAI Proxy",
          authStrategy: "",
          apiKeyHeaderName: "",
          extraHeadersText: '{ "Authorization": "Bearer should-not-be-here" }',
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
    auth_strategy: null,
    api_key_header_name: null,
    extra_headers: null,
    is_active: true,
    last_verified_at: null,
    ...overrides,
  };
}
