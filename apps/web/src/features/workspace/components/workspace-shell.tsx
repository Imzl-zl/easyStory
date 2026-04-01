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
import styles from "@/features/workspace/components/workspace-shell.module.css";
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

  useEffect(() => {
    if (currentProjectId) {
      setLastProjectId(currentProjectId);
    }
  }, [currentProjectId, setLastProjectId]);

  return (
    <AuthGuard>
      <a className={styles.skipLink} href="#workspace-main">跳到主内容</a>
      <div className={styles.shell} data-page-mode={pageMode}>
        <WorkspaceHeader
          currentProjectId={currentProjectId}
          onLogout={clearSession}
          pageMode={pageMode}
          pathname={pathname}
          userName={user?.username ?? "未登录"}
          workspaceItems={workspaceItems}
        />
        <main className={pageMode === "studio" ? styles.contentFull : styles.content} id="workspace-main">
          <div className={pageMode === "studio" ? styles.contentStage : styles.contentInner}>{children}</div>
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
      <header className={styles.topbar}>
        <div className={styles.topbarInner}>
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
    <header className={pageMode === "studio" ? styles.studioTopbar : styles.projectTopbar}>
      <div className={styles.projectTopbarInner}>
        <div className={styles.projectTopbarPrimary}>
          <Link className={styles.backLink} href="/workspace/lobby">
            <span aria-hidden="true">←</span>
            返回书架
          </Link>
          <div className={styles.projectCopy}>
            <span className={styles.projectEyebrow}>当前项目</span>
            <span className={styles.projectTitle}>{resolveContextTitle(pathname)}</span>
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
    <Link className={styles.brandLink} href="/workspace/lobby">
      <span className={styles.brandEyebrow}>easyStory</span>
      <span className={styles.brandTitle}>写作空间</span>
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
    <nav aria-label="工作台导航" className={variant === "project" ? styles.projectNav : styles.nav}>
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
      <span aria-disabled="true" className={styles.navLinkDisabled} title="请先打开一个项目">
        {item.label}
      </span>
    );
  }

  return (
    <Link
      className={styles.navLink}
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
    <div className={styles.actions}>
      <Link className={styles.actionLink} href={settingsHref}>
        {settingsLabel}
      </Link>
      <div className={styles.userChip}>
        <Avatar size={28}>{resolveWorkspaceUserBadge(userName)}</Avatar>
        <span className={styles.userName}>{userName}</span>
      </div>
      <button className={styles.logoutButton} onClick={onLogout} type="button">
        退出
      </button>
    </div>
  );
}
