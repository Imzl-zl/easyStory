import assert from "node:assert/strict";
import test from "node:test";

import {
  applyCredentialUserAgentPreset,
  buildResolvedCredentialUserAgentPreview,
  detectCredentialUserAgentPreset,
  normalizeCredentialUserAgentOverride,
} from "./credential-center-user-agent-support";

test("detectCredentialUserAgentPreset recognizes built-in templates", () => {
  assert.equal(
    detectCredentialUserAgentPreset("codex-cli/0.118.0 (server; node)"),
    "codex-cli",
  );
  assert.equal(
    detectCredentialUserAgentPreset("something-custom/1.0"),
    "custom",
  );
  assert.equal(detectCredentialUserAgentPreset("   "), "");
});

test("applyCredentialUserAgentPreset fills or clears override text", () => {
  assert.equal(
    applyCredentialUserAgentPreset("claude-code", ""),
    "claude-code/2.1.76 (server; node)",
  );
  assert.equal(applyCredentialUserAgentPreset("", "codex-cli/0.118.0 (server; node)"), "");
  assert.equal(applyCredentialUserAgentPreset("custom", "my-proxy/1.0"), "my-proxy/1.0");
});

test("buildResolvedCredentialUserAgentPreview prefers override over generated identity", () => {
  assert.equal(
    buildResolvedCredentialUserAgentPreview({
      clientName: "easyStory",
      clientVersion: "0.1",
      runtimeKind: "server-python",
      userAgentOverride: "codex-cli/0.118.0 (server; node)",
    }),
    "codex-cli/0.118.0 (server; node)",
  );
  assert.equal(
    buildResolvedCredentialUserAgentPreview({
      clientName: "easyStory",
      clientVersion: "0.1",
      runtimeKind: "server-python",
      userAgentOverride: "",
    }),
    "easyStory/0.1 (server; python)",
  );
});

test("normalizeCredentialUserAgentOverride rejects multi-line values", () => {
  assert.throws(
    () => normalizeCredentialUserAgentOverride("bad\nvalue"),
    /不能包含换行/,
  );
});
