"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Avatar } from "@arco-design/web-react";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import {
  buildWorkspaceItems,
  isWorkspaceItemActive,
  resolveWorkspaceProjectId,
  resolveWorkspaceUserBadge,
  type WorkspaceNavItem,
} from "@/features/workspace/components/workspace-shell-support";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

type PageMode = "lobby" | "studio" | "project";

function resolvePageMode(pathname: string): PageMode {
  if (pathname.includes("/lobby") || pathname === "/workspace") {
    return "lobby";
  }
  if (pathname.includes("/studio")) {
    return "studio";
  }
  return "project";
}

function resolveContextTitle(pathname: string): string {
  if (pathname.includes("/studio")) return "创作工作台";
  if (pathname.includes("/engine")) return "作品推进";
  if (pathname.includes("/lab")) return "作品洞察";
  if (pathname.includes("/settings")) return "项目设置";
  return "当前项目";
}

function resolveSettingsHref(currentProjectId: string | null): string {
  if (currentProjectId) {
    return `/workspace/project/${currentProjectId}/settings`;
  }
  return "/workspace/lobby/settings?tab=assistant";
}

export function WorkspaceShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const lastProjectId = useWorkspaceStore((state) => state.lastProjectId);
  const setLastProjectId = useWorkspaceStore((state) => state.setLastProjectId);
  const currentProjectId = resolveWorkspaceProjectId(pathname);
  const workspaceItems = buildWorkspaceItems(currentProjectId, lastProjectId);
  const pageMode = resolvePageMode(pathname);
  const shellClassName = pageMode === "studio"
    ? "flex h-[100dvh] flex-col overflow-hidden [background:var(--workspace-shell-accent-gradient),var(--bg-canvas)]"
    : "min-h-screen pb-[max(env(safe-area-inset-bottom),0px)] [background:var(--workspace-shell-accent-gradient),var(--bg-canvas)]";

  useEffect(() => {
    if (currentProjectId) {
      setLastProjectId(currentProjectId);
    }
  }, [currentProjectId, setLastProjectId]);

  return (
    <AuthGuard>
      <a className="absolute top-3 left-3 z-30 -translate-y-[140%] focus-visible:translate-y-0" href="#workspace-main">跳到主内容</a>
      <div className={shellClassName} data-page-mode={pageMode}>
        <WorkspaceHeader
          currentProjectId={currentProjectId}
          onLogout={clearSession}
          pageMode={pageMode}
          pathname={pathname}
          userName={user?.username ?? "未登录"}
          workspaceItems={workspaceItems}
        />
        <main className={pageMode === "studio" ? "w-full flex-1 min-h-0 overflow-hidden" : "w-[min(100%-2.5rem,1560px)] mx-auto"} id="workspace-main">
          <div className={pageMode === "studio" ? "h-full min-h-0 overflow-hidden" : "min-h-[calc(100vh-72px)] py-5 pb-7"}>{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}

function WorkspaceHeader({
  currentProjectId,
  onLogout,
  pageMode,
  pathname,
  userName,
  workspaceItems,
}: Readonly<{
  currentProjectId: string | null;
  onLogout: () => void;
  pageMode: PageMode;
  pathname: string;
  userName: string;
  workspaceItems: WorkspaceNavItem[];
}>) {
  if (pageMode === "lobby") {
    return (
      <header className="sticky top-0 z-20 border-b border-line-soft bg-glass-heavy backdrop-blur-xl">
        <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 md:gap-6 w-[min(100%-2.5rem,1560px)] mx-auto py-3 md:py-3.5">
          <WorkspaceBrand />
          <WorkspaceNav items={workspaceItems} pathname={pathname} />
          <WorkspaceActions
            onLogout={onLogout}
            settingsHref="/workspace/lobby/settings?tab=assistant"
            settingsLabel="我的助手"
            userName={userName}
          />
        </div>
      </header>
    );
  }

  return (
    <header className={`sticky top-0 z-20 border-b backdrop-blur-xl ${pageMode === "studio" ? "border-line-soft/50 bg-glass-heavy" : "border-line-soft bg-glass-heavy/90"}`}>
      <div className={`grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 md:gap-5 w-[min(100%-2.5rem,1560px)] mx-auto ${pageMode === "studio" ? "py-2.5" : "py-3"}`}>
        <div className="flex items-center gap-4 min-w-0">
          <Link className="inline-flex items-center gap-1.5 text-text-secondary text-sm font-medium whitespace-nowrap hover:text-text-primary transition-colors duration-fast" href="/workspace/lobby">
            <span aria-hidden="true">←</span>
            返回书架
          </Link>
          <div className="grid gap-0.5 min-w-0">
            <span className="text-text-tertiary text-[0.68rem] tracking-[0.14em] uppercase">当前项目</span>
            <span className="overflow-hidden text-text-primary text-sm font-semibold tracking-[-0.02em] text-ellipsis whitespace-nowrap">{resolveContextTitle(pathname)}</span>
          </div>
        </div>
        <WorkspaceNav
          items={workspaceItems.filter((item) => item.segment !== "lobby")}
          pathname={pathname}
          variant="project"
        />
        <WorkspaceActions
          onLogout={onLogout}
          settingsHref={resolveSettingsHref(currentProjectId)}
          settingsLabel="项目设置"
          userName={userName}
        />
      </div>
    </header>
  );
}

function WorkspaceBrand() {
  return (
    <Link className="inline-flex flex-col gap-0.5 min-w-0" href="/workspace/lobby">
      <span className="text-text-tertiary text-[0.68rem] tracking-[0.14em] uppercase font-medium">easyStory</span>
      <span className="text-text-primary text-lg font-semibold tracking-[-0.03em]">写作空间</span>
    </Link>
  );
}

function WorkspaceNav({
  items,
  pathname,
  variant = "default",
}: Readonly<{
  items: WorkspaceNavItem[];
  pathname: string;
  variant?: "default" | "project";
}>) {
  return (
    <nav aria-label="工作台导航" className={`flex min-w-0 items-center gap-1 overflow-x-auto scrollbar-hide ${variant === "project" ? "justify-center" : ""}`}>
      {items.map((item) => (
        <WorkspaceNavLink item={item} key={`${variant}-${item.segment}`} pathname={pathname} />
      ))}
    </nav>
  );
}

function WorkspaceNavLink({
  item,
  pathname,
}: Readonly<{
  item: WorkspaceNavItem;
  pathname: string;
}>) {
  const isActive = isWorkspaceItemActive(item, pathname);
  if (!item.href) {
    return (
      <span aria-disabled="true" className="relative inline-flex items-center h-8 px-2.5 text-text-tertiary text-sm font-medium whitespace-nowrap opacity-40 cursor-not-allowed" title={item.meta || "请先打开一个项目"}>
        {item.label}
      </span>
    );
  }

  return (
    <Link
      className="relative inline-flex items-center h-8 px-2.5 text-text-secondary text-sm font-medium whitespace-nowrap rounded-2xl transition-colors duration-fast hover:text-text-primary hover:bg-surface-hover [&[data-active='true']]:text-accent-primary [&[data-active='true']]:bg-accent-soft"
      data-active={isActive ? "true" : "false"}
      href={item.href}
      title={item.meta}
    >
      {item.label}
    </Link>
  );
}

function WorkspaceActions({
  onLogout,
  settingsHref,
  settingsLabel,
  userName,
}: Readonly<{
  onLogout: () => void;
  settingsHref: string;
  settingsLabel: string;
  userName: string;
}>) {
  return (
    <div className="inline-flex min-w-0 items-center justify-end gap-1.5 md:gap-2.5">
      <Link className="hidden md:inline-flex items-center justify-center h-8 px-3.5 rounded-pill bg-surface shadow-xs text-text-primary text-sm font-medium transition-all duration-fast hover:bg-surface-hover hover:shadow-sm" href={settingsHref}>
        {settingsLabel}
      </Link>
      <div className="inline-flex min-w-0 items-center gap-2 py-1 px-2.5 rounded-pill bg-accent-soft">
        <Avatar size={28}>{resolveWorkspaceUserBadge(userName)}</Avatar>
        <span className="max-w-[8rem] overflow-hidden text-text-primary text-sm font-semibold text-ellipsis whitespace-nowrap max-md:hidden">{userName}</span>
      </div>
      <button className="inline-flex items-center justify-center h-8 px-3.5 rounded-pill bg-surface shadow-xs text-text-secondary text-sm font-medium cursor-pointer transition-all duration-fast hover:bg-surface-hover hover:shadow-sm hover:text-text-primary" onClick={onLogout} type="button">
        退出
      </button>
    </div>
  );
}
