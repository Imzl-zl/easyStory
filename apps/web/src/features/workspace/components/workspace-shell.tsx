"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import {
  resolveWorkspaceProjectId,
  resolveWorkspaceUserBadge,
} from "@/features/workspace/components/workspace-shell-support";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

type PageMode = "lobby" | "project" | "project-workspace";

function resolvePageMode(pathname: string): PageMode {
  if (pathname.includes("/lobby") || pathname === "/workspace") {
    return "lobby";
  }
  if (pathname.includes("/studio") || pathname.includes("/engine") || pathname.includes("/lab")) {
    return "project-workspace";
  }
  return "project";
}

function resolveContextTitle(pathname: string): string {
  if (pathname.includes("/studio")) return "创作工作台";
  if (pathname.includes("/engine")) return "工作流引擎";
  if (pathname.includes("/lab")) return "分析实验室";
  if (pathname.includes("/settings")) return "项目设置";
  return "当前项目";
}

function BackArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 12H5" />
      <path d="M12 19l-7-7 7-7" />
    </svg>
  );
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
  const pageMode = resolvePageMode(pathname);
  const shellClassName = pageMode === "project-workspace"
    ? "workspace-shell--studio"
    : "workspace-shell--default";

  useEffect(() => {
    if (currentProjectId) {
      setLastProjectId(currentProjectId);
    }
  }, [currentProjectId, setLastProjectId]);

  // Lobby page renders its own full-viewport layout; skip shell chrome
  if (pageMode === "lobby") {
    return (
      <AuthGuard>
        <a className="absolute top-3 left-3 z-50 -translate-y-[140%] focus-visible:translate-y-0" href="#workspace-main">跳到主内容</a>
        <div className={shellClassName} data-page-mode={pageMode}>
          <main className="w-full" id="workspace-main">{children}</main>
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <a className="absolute top-3 left-3 z-30 -translate-y-[140%] focus-visible:translate-y-0" href="#workspace-main">跳到主内容</a>
      <div className={shellClassName} data-page-mode={pageMode}>
        <WorkspaceHeader
          currentProjectId={currentProjectId}
          onLogout={clearSession}
          pathname={pathname}
          userName={user?.username ?? "未登录"}
        />
        <main className={pageMode === "project-workspace" ? "w-full flex-1 min-h-0 overflow-hidden" : "w-[min(100%-2.5rem,1560px)] mx-auto"} id="workspace-main">
          <div className={pageMode === "project-workspace" ? "h-full min-h-0 overflow-hidden" : "min-h-[calc(100vh-72px)] py-5 pb-7"}>{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}

function WorkspaceHeader({
  currentProjectId,
  onLogout,
  pathname,
  userName,
}: Readonly<{
  currentProjectId: string | null;
  onLogout: () => void;
  pathname: string;
  userName: string;
}>) {
  return (
    <header className="workspace-header--project">
      <div className="workspace-header__inner">
        <div className="workspace-header__left">
          <Link className="workspace-header__back" href="/workspace/lobby">
            <BackArrowIcon />
            <span>返回书架</span>
          </Link>
          <div className="workspace-header__divider" />
          <span className="workspace-header__page-title">{resolveContextTitle(pathname)}</span>
        </div>
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
    <div className="workspace-header__actions">
      <Link className="workspace-header__action-link" href={settingsHref}>
        {settingsLabel}
      </Link>
      <div className="workspace-header__user">
        <div className="workspace-header__avatar">
          {resolveWorkspaceUserBadge(userName)}
        </div>
        <span className="workspace-header__username">{userName}</span>
      </div>
      <button className="workspace-header__logout" onClick={onLogout} type="button">
        退出
      </button>
    </div>
  );
}
