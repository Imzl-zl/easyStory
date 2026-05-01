import assert from "node:assert/strict";
import test from "node:test";

import {
  getNextSidebarPreference,
  resolveWorkspaceProjectId,
  resolveWorkspaceSidebarCollapsed,
  resolveWorkspaceSidebarWidth,
  resolveWorkspaceUserBadge,
  shouldShowWorkspaceSidebarToggle,
} from "./workspace-shell-support";

test("resolveWorkspaceProjectId returns the project id only for project workspace paths", () => {
  assert.equal(resolveWorkspaceProjectId("/workspace/project/p1/studio"), "p1");
  assert.equal(resolveWorkspaceProjectId("/workspace/lobby"), null);
});

test("workspace shell helpers resolve user badge and next preference deterministically", () => {
  assert.equal(resolveWorkspaceUserBadge("张三"), "张");
  assert.equal(resolveWorkspaceUserBadge(""), "客");
  assert.equal(getNextSidebarPreference("expanded"), "collapsed");
  assert.equal(resolveWorkspaceSidebarWidth(true), "88px");
});

test("resolveWorkspaceSidebarCollapsed forces mobile into collapsed mode and respects desktop preference", () => {
  assert.equal(
    resolveWorkspaceSidebarCollapsed({
      hasHydrated: false,
      isMobileViewport: true,
      sidebarPreference: "expanded",
    }),
    true,
  );
  assert.equal(
    resolveWorkspaceSidebarCollapsed({
      hasHydrated: true,
      isMobileViewport: false,
      sidebarPreference: "collapsed",
    }),
    true,
  );
  assert.equal(
    resolveWorkspaceSidebarCollapsed({
      hasHydrated: false,
      isMobileViewport: false,
      sidebarPreference: "collapsed",
    }),
    false,
  );
  assert.equal(shouldShowWorkspaceSidebarToggle(true), false);
});
