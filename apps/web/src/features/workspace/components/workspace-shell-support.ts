import type { WorkspaceSidebarPreference } from "@/lib/stores/workspace-store";

const PROJECT_PATH_PATTERN = /^\/workspace\/project\/([^/]+)\//;
const PROJECT_SETTINGS_PATH_PATTERN = /^\/workspace\/project\/[^/]+\/settings(?:\/|$)/;
const LOBBY_PATH_PREFIX = "/workspace/lobby";
const PROJECT_WORKSPACE_ITEMS = [
  { label: "工作室", meta: "当前项目", segment: "studio", shortLabel: "作" },
  { label: "引擎", meta: "当前项目", segment: "engine", shortLabel: "引" },
  { label: "实验室", meta: "当前项目", segment: "lab", shortLabel: "析" },
] as const;
const WORKSPACE_SIDEBAR_WIDTH = {
  collapsed: "72px",
  expanded: "220px",
} as const;

type WorkspaceSegment = "lobby" | "studio" | "engine" | "lab";

export type WorkspaceNavItem = {
  disabled: boolean;
  href: string | null;
  label: string;
  meta: string;
  segment: WorkspaceSegment;
  shortLabel: string;
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
      label: "项目大厅",
      meta: "项目",
      segment: "lobby",
      shortLabel: "厅",
    },
    ...PROJECT_WORKSPACE_ITEMS.map((item) => ({
      disabled: projectId === null,
      href: projectId ? `/workspace/project/${projectId}/${item.segment}` : null,
      label: item.label,
      meta: item.meta,
      segment: item.segment,
      shortLabel: item.shortLabel,
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
