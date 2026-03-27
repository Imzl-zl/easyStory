import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";
import {
  buildCredentialDeleteImpactItems,
  getCredentialScopeLabel,
} from "./credential-delete-confirm-support";

test("project credential delete impacts describe override removal and fallback order", () => {
  const items = buildCredentialDeleteImpactItems(createCredential({ owner_type: "project" }));
  assert.equal(getCredentialScopeLabel(createCredential({ owner_type: "project" })), "项目级模型连接");
  assert.equal(items[0], "删除后，项目级连接标识「openai」将不再覆盖同标识的全局连接。");
  assert.match(items[1], /继续使用全局连接/);
  assert.match(items[3], /用量历史/);
});

test("inactive global credential delete impacts stay explicit about non-active status", () => {
  const items = buildCredentialDeleteImpactItems(createCredential({ is_active: false }));
  assert.equal(getCredentialScopeLabel(createCredential()), "全局模型连接");
  assert.equal(items[0], "这条连接当前已停用；删除后只会移除全局记录，不会影响当前已停用状态。");
  assert.match(items[1], /项目级连接始终优先于全局连接/);
  assert.match(items[4], /删除审计记录/);
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
