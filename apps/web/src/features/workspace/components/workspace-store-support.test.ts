import assert from "node:assert/strict";
import test from "node:test";

import { buildWorkspacePersistedState, useWorkspaceStore } from "@/lib/stores/workspace-store";

test("buildWorkspacePersistedState keeps only durable workspace fields", () => {
  const persisted = buildWorkspacePersistedState({
    clearProjectContext: () => {},
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

test("workspace store clears project context without wiping sidebar preference", () => {
  useWorkspaceStore.setState({
    hasHydrated: true,
    lastProjectId: "project-1",
    lastWorkflowByProject: { "project-1": "workflow-9" },
    sidebarPreference: "collapsed",
  });

  useWorkspaceStore.getState().clearProjectContext();

  const state = useWorkspaceStore.getState();
  assert.equal(state.lastProjectId, null);
  assert.deepEqual(state.lastWorkflowByProject, {});
  assert.equal(state.sidebarPreference, "collapsed");

  useWorkspaceStore.setState({
    hasHydrated: true,
    lastProjectId: null,
    lastWorkflowByProject: {},
    sidebarPreference: "expanded",
  });
});
