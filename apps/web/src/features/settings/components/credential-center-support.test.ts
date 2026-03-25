import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";
import {
  buildCredentialCreatePayload,
  buildCredentialUpdatePayload,
  createCredentialFormFromView,
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
  });
});

test("buildCredentialUpdatePayload only sends changed fields and rotates key when provided", () => {
  const payload = buildCredentialUpdatePayload(createCredential(), {
    apiDialect: "anthropic_messages",
    apiKey: "rotated-key",
    baseUrl: "https://proxy.example.com",
    defaultModel: "claude-sonnet-4-20250514",
    displayName: "Anthropic Proxy",
    provider: "openai",
  });
  assert.deepEqual(payload, {
    api_dialect: "anthropic_messages",
    api_key: "rotated-key",
    base_url: "https://proxy.example.com",
    default_model: "claude-sonnet-4-20250514",
    display_name: "Anthropic Proxy",
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
        provider: "openai",
      }),
    /不支持清空默认模型/,
  );
});

test("normalizeOptionalQueryValue trims blank query params to null", () => {
  assert.equal(normalizeOptionalQueryValue(" credential-1 "), "credential-1");
  assert.equal(normalizeOptionalQueryValue("   "), null);
  assert.equal(normalizeOptionalQueryValue(null), null);
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
    is_active: true,
    last_verified_at: null,
    ...overrides,
  };
}
