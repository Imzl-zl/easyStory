import assert from "node:assert/strict";
import test from "node:test";

import {
  buildProjectSettingsPathWithParams,
  isValidProjectSettingsTab,
  normalizeProjectAuditEventType,
  resolveProjectSettingsTab,
} from "./project-settings-support";

test("resolveProjectSettingsTab falls back to setting for invalid values", () => {
  assert.equal(resolveProjectSettingsTab("audit"), "audit");
  assert.equal(resolveProjectSettingsTab("setting"), "setting");
  assert.equal(resolveProjectSettingsTab("unknown"), "setting");
  assert.equal(resolveProjectSettingsTab(null), "setting");
  assert.equal(isValidProjectSettingsTab("audit"), true);
  assert.equal(isValidProjectSettingsTab("invalid"), false);
});

test("normalizeProjectAuditEventType trims blanks to null", () => {
  assert.equal(normalizeProjectAuditEventType(" project.setting.updated "), "project.setting.updated");
  assert.equal(normalizeProjectAuditEventType("   "), null);
  assert.equal(normalizeProjectAuditEventType(null), null);
});

test("buildProjectSettingsPathWithParams updates and removes params", () => {
  assert.equal(
    buildProjectSettingsPathWithParams(
      "/workspace/project/p1/settings",
      "tab=audit&event=project.updated",
      { event: "project.created" },
    ),
    "/workspace/project/p1/settings?tab=audit&event=project.created",
  );
  assert.equal(
    buildProjectSettingsPathWithParams(
      "/workspace/project/p1/settings",
      "tab=audit&event=project.updated",
      { event: null, tab: null },
    ),
    "/workspace/project/p1/settings",
  );
});
