import type { WorkspaceSidebarPreference } from "@/lib/stores/workspace-store";

const PROJECT_PATH_PATTERN = /^\/workspace\/project\/([^/]+)\//;
const WORKSPACE_SIDEBAR_WIDTH = {
  collapsed: "88px",
  expanded: "280px",
} as const;

export function getNextSidebarPreference(
  currentPreference: WorkspaceSidebarPreference,
): WorkspaceSidebarPreference {
  return currentPreference === "collapsed" ? "expanded" : "collapsed";
}

export function resolveWorkspaceSidebarCollapsed({
  hasHydrated,
  isMobileViewport,
  sidebarPreference,
}: Readonly<{
  hasHydrated: boolean;
  isMobileViewport: boolean;
  sidebarPreference: WorkspaceSidebarPreference;
}>) {
  if (isMobileViewport) {
    return true;
  }
  return hasHydrated && sidebarPreference === "collapsed";
}

export function resolveWorkspaceProjectId(pathname: string): string | null {
  return pathname.match(PROJECT_PATH_PATTERN)?.[1] ?? null;
}

export function resolveWorkspaceSidebarWidth(isCollapsed: boolean) {
  return isCollapsed ? WORKSPACE_SIDEBAR_WIDTH.collapsed : WORKSPACE_SIDEBAR_WIDTH.expanded;
}

export function resolveWorkspaceUserBadge(username: string | null | undefined) {
  const value = username?.trim();
  return value ? Array.from(value)[0] ?? "客" : "客";
}

export function shouldShowWorkspaceSidebarToggle(isMobileViewport: boolean) {
  return !isMobileViewport;
}
