import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeApiKeyHeaderName,
  parseExtraHeadersText,
} from "./credential-center-compatibility-support";

test("normalizeApiKeyHeaderName rejects non-token header names", () => {
  assert.throws(
    () => normalizeApiKeyHeaderName("openai_chat_completions", "custom_header", "bad@header"),
    /合法的 HTTP 请求头名称/,
  );
});

test("parseExtraHeadersText rejects non-token header names", () => {
  assert.throws(
    () => parseExtraHeadersText('{ "bad@header": "trace-001" }'),
    /不是合法的 HTTP 请求头名称/,
  );
});

test("parseExtraHeadersText rejects runtime-managed user-agent header", () => {
  assert.throws(
    () =>
      parseExtraHeadersText('{ "User-Agent": "fake-cli" }', {
        apiDialect: "openai_chat_completions",
      }),
    /系统托管的请求头/,
  );
});
