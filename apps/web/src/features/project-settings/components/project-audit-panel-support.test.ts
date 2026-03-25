import assert from "node:assert/strict";
import test from "node:test";

import type { AuditLogView } from "@/lib/api/types";

import {
  buildProjectAuditQueryKey,
  formatProjectAuditTarget,
  formatProjectAuditTime,
  summarizeProjectAuditDetails,
} from "./project-audit-panel-support";

test("summarizeProjectAuditDetails exposes top-level detail keys", () => {
  assert.equal(summarizeProjectAuditDetails(null), "无详情字段");
  assert.equal(
    summarizeProjectAuditDetails({ after: "x", before: "y", impact: { count: 2 } }),
    "after · before · impact",
  );
  assert.equal(
    summarizeProjectAuditDetails({ a: 1, b: 2, c: 3, d: 4 }),
    "a · b · c 等 4 项",
  );
});

test("formatProjectAuditTarget renders concise entity identity", () => {
  const log = createAuditLog();
  assert.equal(formatProjectAuditTarget(log), "project · 12345678");
});

test("formatProjectAuditTime uses UTC formatting", () => {
  assert.equal(formatProjectAuditTime("2026-03-25T06:08:00Z"), "03/25 06:08 UTC");
});

test("buildProjectAuditQueryKey keeps null as the no-filter state", () => {
  assert.deepEqual(buildProjectAuditQueryKey("project-1", null), ["project-audit", "project-1", null]);
  assert.deepEqual(
    buildProjectAuditQueryKey("project-1", "project.updated"),
    ["project-audit", "project-1", "project.updated"],
  );
});

function createAuditLog(): AuditLogView {
  return {
    actor_user_id: null,
    created_at: "2026-03-25T12:00:00Z",
    details: null,
    entity_id: "12345678-1234-5678-1234-567812345678",
    entity_type: "project",
    event_type: "project.updated",
    id: "audit-1",
  };
}
