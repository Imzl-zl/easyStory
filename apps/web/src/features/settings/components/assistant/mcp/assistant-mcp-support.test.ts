import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantMcpDocumentPreview,
  buildAssistantMcpListDescription,
  buildAssistantMcpPayload,
  createEmptyAssistantMcpDraft,
  parseAssistantMcpDocument,
  sanitizeAssistantMcpTimeoutInput,
} from "@/features/settings/components/assistant/mcp/assistant-mcp-support";

test("assistant mcp support creates a lean default draft", () => {
  const draft = createEmptyAssistantMcpDraft();
  assert.equal(draft.enabled, true);
  assert.equal(draft.timeout, "30");
  assert.equal(draft.transport, "streamable_http");
});

test("assistant mcp support builds normalized payloads", () => {
  const payload = buildAssistantMcpPayload({
    description: " 给 Hook 调用的资料工具 ",
    enabled: true,
    headers: { " X-Test ": " demo " },
    name: " 资料检索 ",
    timeout: " 45 ",
    transport: " streamable_http ",
    url: " https://example.com/mcp ",
    version: " 1.0.0 ",
  });

  assert.deepEqual(payload, {
    description: "给 Hook 调用的资料工具",
    enabled: true,
    headers: { "X-Test": "demo" },
    name: "资料检索",
    timeout: 45,
    transport: "streamable_http",
    url: "https://example.com/mcp",
    version: "1.0.0",
  });
});

test("assistant mcp support builds yaml preview", () => {
  const preview = buildAssistantMcpDocumentPreview(
    {
      description: "给 Hook 调用的资料工具",
      enabled: true,
      headers: { "X-Test": "demo" },
      name: "资料检索",
      timeout: "45",
      transport: "streamable_http",
      url: "https://example.com/mcp",
      version: "1.0.0",
    },
    { serverId: "mcp.user.research-abc123" },
  );

  assert.match(preview, /^mcp_server:/);
  assert.match(preview, /id: mcp\.user\.research-abc123/);
  assert.match(preview, /name: "资料检索"/);
  assert.match(preview, /url: "https:\/\/example\.com\/mcp"/);
  assert.match(preview, /timeout: 45/);
});

test("assistant mcp support parses yaml documents back into drafts", () => {
  const parsed = parseAssistantMcpDocument(`mcp_server:
  name: "资料检索"
  enabled: true
  version: "1.0.0"
  description: "给 Hook 调用的资料工具"
  transport: "streamable_http"
  url: "https://example.com/mcp"
  headers: {"X-Test":"demo"}
  timeout: 45`);

  assert.deepEqual(parsed, {
    description: "给 Hook 调用的资料工具",
    enabled: true,
    headers: { "X-Test": "demo" },
    name: "资料检索",
    timeout: "45",
    transport: "streamable_http",
    url: "https://example.com/mcp",
    version: "1.0.0",
  });
});

test("assistant mcp support summarizes host when description is missing", () => {
  assert.equal(
    buildAssistantMcpListDescription({
      description: null,
      enabled: true,
      transport: "streamable_http",
      url: "https://example.com/mcp",
    }),
    "example.com · streamable_http",
  );
  assert.equal(sanitizeAssistantMcpTimeoutInput(" 4a5 "), "45");
});
