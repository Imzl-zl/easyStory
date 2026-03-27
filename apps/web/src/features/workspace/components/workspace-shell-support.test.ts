import assert from "node:assert/strict";
import test from "node:test";

import {
  buildWorkspaceItems,
  getNextSidebarPreference,
  isWorkspaceItemActive,
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

test("buildWorkspaceItems reuses the last project when route context is absent", () => {
  const items = buildWorkspaceItems(null, "project-2");
  assert.equal(items[0]?.href, "/workspace/lobby");
  assert.equal(items[1]?.href, "/workspace/project/project-2/studio");
  assert.equal(items[3]?.shortLabel, "析");
});

test("buildWorkspaceItems disables project views when no current project exists", () => {
  const items = buildWorkspaceItems(null, null);
  assert.equal(items[1]?.disabled, true);
  assert.equal(items[1]?.href, null);
});

test("isWorkspaceItemActive treats project settings as part of studio", () => {
  const studio = buildWorkspaceItems("project-1", null)[1]!;
  const lobby = buildWorkspaceItems("project-1", null)[0]!;
  assert.equal(isWorkspaceItemActive(studio, "/workspace/project/project-1/settings"), true);
  assert.equal(isWorkspaceItemActive(lobby, "/workspace/lobby/settings"), true);
  assert.equal(isWorkspaceItemActive(studio, "/workspace/project/project-1/engine"), false);
});

test("workspace shell helpers resolve user badge and next preference deterministically", () => {
  assert.equal(resolveWorkspaceUserBadge("张三"), "张");
  assert.equal(resolveWorkspaceUserBadge(""), "客");
  assert.equal(getNextSidebarPreference("expanded"), "collapsed");
  assert.equal(resolveWorkspaceSidebarWidth(true), "72px");
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
