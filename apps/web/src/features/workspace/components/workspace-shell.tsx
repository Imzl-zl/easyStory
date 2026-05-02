"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import {
  resolveWorkspaceProjectId,
  resolveWorkspaceUserBadge,
} from "@/features/workspace/components/workspace-shell-support";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

type PageMode = "lobby" | "project" | "project-workspace" | "sub-page";

function resolvePageMode(pathname: string): PageMode {
  if (pathname.includes("/recycle-bin") || pathname.includes("/lobby/settings")) {
    return "sub-page";
  }
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
  if (pathname.includes("/recycle-bin")) return "回收站";
  if (pathname.includes("/lobby/settings")) return "全局设置";
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

export function WorkspaceShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const lastProjectId = useWorkspaceStore((state) => state.lastProjectId);
  const setLastProjectId = useWorkspaceStore((state) => state.setLastProjectId);
  const currentProjectId = resolveWorkspaceProjectId(pathname);
  const pageMode = resolvePageMode(pathname);
  const shellClassName = pageMode === "project-workspace" || pageMode === "sub-page"
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
          onLogout={clearSession}
          pathname={pathname}
          userName={user?.username ?? "未登录"}
        />
        <main className={pageMode === "project-workspace" || pageMode === "sub-page" ? "w-full flex-1 min-h-0 overflow-hidden" : "w-[min(100%-2.5rem,1560px)] mx-auto"} id="workspace-main">
          <div className={pageMode === "project-workspace" || pageMode === "sub-page" ? "h-full min-h-0 overflow-hidden" : "min-h-[calc(100vh-72px)] py-5 pb-7"}>{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}

function WorkspaceHeader({
  onLogout,
  pathname,
  userName,
}: Readonly<{
  onLogout: () => void;
  pathname: string;
  userName: string;
}>) {
  return (
    <header className="workspace-header--project">
      <div className="workspace-header__inner">
        <div className="workspace-header__left">
          <button className="workspace-header__back" onClick={() => window.history.back()} type="button">
            <BackArrowIcon />
            <span>返回</span>
          </button>
          <div className="workspace-header__divider" />
          <span className="workspace-header__page-title">{resolveContextTitle(pathname)}</span>
        </div>
        <WorkspaceActions
          onLogout={onLogout}
          userName={userName}
        />
      </div>
    </header>
  );
}

function WorkspaceActions({
  onLogout,
  userName,
}: Readonly<{
  onLogout: () => void;
  userName: string;
}>) {
  return (
    <div className="workspace-header__actions">
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
