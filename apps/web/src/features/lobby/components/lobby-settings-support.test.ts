import assert from "node:assert/strict";
import test from "node:test";

import {
  isValidLobbySettingsTab,
  isValidCredentialCenterMode,
  isValidCredentialCenterScope,
  normalizeCredentialSettingsPath,
  normalizeLobbySettingsPath,
  resolveLobbySettingsTab,
  resolveCredentialCenterMode,
  resolveCredentialCenterScope,
} from "./lobby-settings-support";

test("lobby settings tab resolves to supported values", () => {
  assert.equal(resolveLobbySettingsTab("assistant-rules"), "assistant");
  assert.equal(resolveLobbySettingsTab("assistant-preferences"), "assistant");
  assert.equal(resolveLobbySettingsTab("assistant-agents"), "agents");
  assert.equal(resolveLobbySettingsTab("assistant-hooks"), "hooks");
  assert.equal(resolveLobbySettingsTab("assistant-mcp"), "mcp");
  assert.equal(resolveLobbySettingsTab("assistant-skills"), "skills");
  assert.equal(resolveLobbySettingsTab("other"), "assistant");
  assert.equal(isValidLobbySettingsTab("agents"), true);
  assert.equal(isValidLobbySettingsTab("credentials"), true);
  assert.equal(isValidLobbySettingsTab("hooks"), true);
  assert.equal(isValidLobbySettingsTab("mcp"), true);
  assert.equal(isValidLobbySettingsTab("assistant-rules"), true);
  assert.equal(isValidLobbySettingsTab("skills"), true);
  assert.equal(isValidLobbySettingsTab("debug"), false);
});

test("credential settings mode and scope resolve to safe defaults", () => {
  assert.equal(resolveCredentialCenterMode("audit"), "audit");
  assert.equal(resolveCredentialCenterMode("unknown"), "list");
  assert.equal(isValidCredentialCenterMode("list"), true);
  assert.equal(isValidCredentialCenterMode("detail"), false);
  assert.equal(resolveCredentialCenterScope("project", "project-1"), "project");
  assert.equal(resolveCredentialCenterScope("project", null), "user");
  assert.equal(resolveCredentialCenterScope("unknown", "project-1"), "user");
  assert.equal(isValidCredentialCenterScope("user"), true);
  assert.equal(isValidCredentialCenterScope("other"), false);
});

test("normalizeCredentialSettingsPath updates and removes query params while keeping tab anchor", () => {
  assert.equal(
    normalizeCredentialSettingsPath("/workspace/lobby/settings", "tab=credentials&scope=project&project=p1", {
      credential: "credential-1",
      scope: "user",
      sub: "audit",
    }),
    "/workspace/lobby/settings?tab=credentials&scope=user&project=p1&credential=credential-1&sub=audit",
  );
  assert.equal(
    normalizeCredentialSettingsPath("/workspace/lobby/settings", "tab=credentials&scope=project&project=p1", {
      credential: null,
      project: null,
      scope: "user",
      sub: "list",
    }),
    "/workspace/lobby/settings?tab=credentials&scope=user&sub=list",
  );
});

test("normalizeLobbySettingsPath can switch top-level tabs without losing query intent", () => {
  assert.equal(
    normalizeLobbySettingsPath("/workspace/lobby/settings", "tab=credentials&scope=user", {
      sub: null,
      tab: "assistant",
    }),
    "/workspace/lobby/settings?tab=assistant&scope=user",
  );
});
