import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";
import {
  buildCredentialDeleteImpactItems,
  getCredentialScopeLabel,
} from "./credential-delete-confirm-support";

test("project credential delete impacts describe override removal and fallback order", () => {
  const items = buildCredentialDeleteImpactItems(createCredential({ owner_type: "project" }));
  assert.equal(getCredentialScopeLabel(createCredential({ owner_type: "project" })), "项目级凭证");
  assert.equal(items[0], "删除后，项目级 provider「openai」将不再覆盖同 provider 的全局凭证。");
  assert.match(items[1], /回退到全局凭证/);
  assert.match(items[3], /token usage 历史/);
});

test("inactive global credential delete impacts stay explicit about non-active status", () => {
  const items = buildCredentialDeleteImpactItems(createCredential({ is_active: false }));
  assert.equal(getCredentialScopeLabel(createCredential()), "全局凭证");
  assert.equal(items[0], "当前凭证已停用；删除只会移除全局记录，不会成为当前运行时的活动凭证来源。");
  assert.match(items[1], /项目级始终优先于全局/);
  assert.match(items[4], /credential_delete/);
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
