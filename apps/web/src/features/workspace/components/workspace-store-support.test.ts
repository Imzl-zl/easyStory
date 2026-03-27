import assert from "node:assert/strict";
import test from "node:test";

import { buildWorkspacePersistedState } from "@/lib/stores/workspace-store";

test("buildWorkspacePersistedState keeps only durable workspace fields", () => {
  const persisted = buildWorkspacePersistedState({
    hasHydrated: true,
    lastProjectId: "project-1",
    lastWorkflowByProject: { "project-1": "workflow-9" },
    markHydrated: () => {},
    setLastProjectId: () => {},
    setLastWorkflow: () => {},
    setSidebarPreference: () => {},
    sidebarPreference: "collapsed",
  });

  assert.deepEqual(persisted, {
    lastProjectId: "project-1",
    lastWorkflowByProject: { "project-1": "workflow-9" },
    sidebarPreference: "collapsed",
  });
  assert.equal("hasHydrated" in persisted, false);
});
