import type { WorkspaceSidebarPreference } from "@/lib/stores/workspace-store";

const PROJECT_PATH_PATTERN = /^\/workspace\/project\/([^/]+)\//;
const PROJECT_SETTINGS_PATH_PATTERN = /^\/workspace\/project\/[^/]+\/settings(?:\/|$)/;
const LOBBY_PATH_PREFIX = "/workspace/lobby";
const PROJECT_WORKSPACE_ITEMS = [
  { label: "创作", meta: "设定、大纲、章节", segment: "studio" },
  { label: "推进", meta: "推进状态与下一步", segment: "engine" },
  { label: "洞察", meta: "对作品的帮助", segment: "lab" },
] as const;
const WORKSPACE_SIDEBAR_WIDTH = {
  collapsed: "88px",
  expanded: "280px",
} as const;

export type WorkspaceSegment = "lobby" | "studio" | "engine" | "lab";

export type WorkspaceNavItem = {
  disabled: boolean;
  href: string | null;
  label: string;
  meta: string;
  segment: WorkspaceSegment;
};

export function buildWorkspaceItems(
  currentProjectId: string | null,
  lastProjectId: string | null,
): WorkspaceNavItem[] {
  const projectId = currentProjectId ?? lastProjectId;
  return [
    {
      disabled: false,
      href: "/workspace/lobby",
      label: "书架",
      meta: "项目与草稿",
      segment: "lobby",
    },
    ...PROJECT_WORKSPACE_ITEMS.map((item) => ({
      disabled: projectId === null,
      href: projectId ? `/workspace/project/${projectId}/${item.segment}` : null,
      label: item.label,
      meta: item.meta,
      segment: item.segment,
    })),
  ];
}

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

export function isWorkspaceItemActive(item: WorkspaceNavItem, pathname: string) {
  if (!item.href) {
    return false;
  }
  if (item.segment === "lobby") {
    return pathname.startsWith(LOBBY_PATH_PREFIX);
  }
  if (item.segment === "studio" && PROJECT_SETTINGS_PATH_PATTERN.test(pathname)) {
    return true;
  }
  return pathname.includes(`/${item.segment}`);
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
