import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";
import { buildCredentialOverrideInfoByCredentialId } from "./credential-center-override-support";

test("buildCredentialOverrideInfoByCredentialId matches active user credentials with active project credentials by provider", () => {
  const overrides = buildCredentialOverrideInfoByCredentialId(
    [
      createCredential({ id: "user-openai", provider: "openai" }),
      createCredential({ id: "user-anthropic", provider: "anthropic", is_active: false }),
      createCredential({ id: "user-gemini", provider: "gemini" }),
    ],
    [
      createCredential({
        id: "project-openai",
        display_name: "Project OpenAI",
        owner_type: "project",
        provider: "openai",
      }),
      createCredential({
        id: "project-anthropic",
        display_name: "Project Anthropic",
        is_active: false,
        owner_type: "project",
        provider: "anthropic",
      }),
    ],
  );
  assert.deepEqual(overrides, {
    "user-openai": {
      projectCredentialDisplayName: "Project OpenAI",
      projectCredentialId: "project-openai",
      provider: "openai",
    },
  });
});

test("buildCredentialOverrideInfoByCredentialId returns empty object when no active project override exists", () => {
  assert.deepEqual(
    buildCredentialOverrideInfoByCredentialId([createCredential()], undefined),
    {},
  );
  assert.deepEqual(
    buildCredentialOverrideInfoByCredentialId([createCredential()], [createCredential({ is_active: false, owner_type: "project" })]),
    {},
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
