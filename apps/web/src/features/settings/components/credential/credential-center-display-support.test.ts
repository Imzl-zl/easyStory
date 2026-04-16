import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialView } from "@/lib/api/types";

import {
  buildCredentialTransportCapabilityItem,
} from "./credential-center-display-support";

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

test("buildCredentialTransportCapabilityItem exposes user-facing detail and tone", () => {
  assert.deepEqual(
    buildCredentialTransportCapabilityItem(
      createCredential({ buffered_tool_verified_probe_kind: "text_probe" }),
      "buffered",
    ),
    {
      detail: "这条链路已经确认能稳定返回文本，工具能力还没验证。",
      lastVerifiedAt: null,
      summary: "基础连接可用",
      title: "非流链路",
      tone: "ready",
    },
  );
  assert.deepEqual(
    buildCredentialTransportCapabilityItem(createCredential(), "stream"),
    {
      detail: "还没执行这条链路的验证。",
      lastVerifiedAt: null,
      summary: "未验证",
      title: "流式链路",
      tone: "draft",
    },
  );
});
