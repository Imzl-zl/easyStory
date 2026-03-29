import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS,
  MAX_ASSISTANT_MAX_OUTPUT_TOKENS,
  resolveAssistantMaxOutputTokens,
  sanitizeAssistantOutputTokenInput,
  toAssistantOutputTokenDraft,
} from "./assistant-output-token-support";

test("assistant output token support sanitizes freeform input", () => {
  assert.equal(sanitizeAssistantOutputTokenInput(" 4a0-96 "), "4096");
});

test("assistant output token support falls back to safe default for invalid values", () => {
  assert.equal(resolveAssistantMaxOutputTokens(""), DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS);
  assert.equal(resolveAssistantMaxOutputTokens("0"), DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS);
  assert.equal(resolveAssistantMaxOutputTokens(64), DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS);
});

test("assistant output token support caps overlarge values and formats draft text", () => {
  assert.equal(resolveAssistantMaxOutputTokens("999999"), MAX_ASSISTANT_MAX_OUTPUT_TOKENS);
  assert.equal(toAssistantOutputTokenDraft(8192), "8192");
});
