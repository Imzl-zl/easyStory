import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";

import { formatCredentialToolCapabilitySummary } from "./credential-center-display-support";

function createCredential(overrides: Partial<CredentialView> = {}): CredentialView {
  return {
    id: "credential-1",
    owner_type: "user",
    owner_id: null,
    provider: "openai",
    api_dialect: "openai_chat_completions",
    display_name: "OpenAI",
    masked_key: "sk-...1234",
    base_url: null,
    default_model: "gpt-4o-mini",
    interop_profile: null,
    stream_tool_verified_probe_kind: null,
    stream_tool_last_verified_at: null,
    buffered_tool_verified_probe_kind: null,
    buffered_tool_last_verified_at: null,
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

test("formatCredentialToolCapabilitySummary reports explicit tool verification levels", () => {
  assert.equal(
    formatCredentialToolCapabilitySummary(
      createCredential({ stream_tool_verified_probe_kind: "tool_continuation_probe" }),
      "stream",
    ),
    "流式工具：已验证完整工具调用",
  );
  assert.equal(
    formatCredentialToolCapabilitySummary(
      createCredential({ buffered_tool_verified_probe_kind: "tool_call_probe" }),
      "buffered",
    ),
    "非流工具：已验证工具调用，未验证结果续接",
  );
  assert.equal(
    formatCredentialToolCapabilitySummary(
      createCredential({ stream_tool_verified_probe_kind: "tool_definition_probe" }),
      "stream",
    ),
    "流式工具：仅验证工具定义",
  );
  assert.equal(
    formatCredentialToolCapabilitySummary(
      createCredential({ buffered_tool_verified_probe_kind: "text_probe" }),
      "buffered",
    ),
    "非流工具：仅验证基础连接",
  );
  assert.equal(
    formatCredentialToolCapabilitySummary(
      createCredential(),
      "stream",
    ),
    "流式工具：未验证",
  );
});
