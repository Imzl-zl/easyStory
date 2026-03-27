"use client";

import type { CSSProperties } from "react";
import { useEffect, useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";
import {
  buildWorkspaceItems,
  getNextSidebarPreference,
  isWorkspaceItemActive,
  resolveWorkspaceProjectId,
  resolveWorkspaceSidebarCollapsed,
  resolveWorkspaceSidebarWidth,
  resolveWorkspaceUserBadge,
  shouldShowWorkspaceSidebarToggle,
  type WorkspaceNavItem,
} from "@/features/workspace/components/workspace-shell-support";
import {
  WorkspaceBrandIcon,
  WorkspaceLogoutIcon,
  WorkspaceNavIcon,
  WorkspaceToggleIcon,
} from "@/features/workspace/components/workspace-shell-icons";
import styles from "@/features/workspace/components/workspace-shell.module.css";

const MOBILE_VIEWPORT_MEDIA_QUERY = "(max-width: 1023px)";

export function WorkspaceShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const hasHydrated = useWorkspaceStore((state) => state.hasHydrated);
  const lastProjectId = useWorkspaceStore((state) => state.lastProjectId);
  const sidebarPreference = useWorkspaceStore((state) => state.sidebarPreference);
  const setLastProjectId = useWorkspaceStore((state) => state.setLastProjectId);
  const setSidebarPreference = useWorkspaceStore((state) => state.setSidebarPreference);
  const isMobileViewport = useIsMobileViewport();
  const currentProjectId = resolveWorkspaceProjectId(pathname);
  const isSidebarCollapsed = resolveWorkspaceSidebarCollapsed({
    hasHydrated,
    isMobileViewport,
    sidebarPreference,
  });
  const workspaceItems = buildWorkspaceItems(currentProjectId, lastProjectId);

  useEffect(() => {
    if (currentProjectId) {
      setLastProjectId(currentProjectId);
    }
  }, [currentProjectId, setLastProjectId]);

  return (
    <AuthGuard>
      <a className={styles.skipLink} href="#workspace-main">跳到主内容</a>
      <div
        className={`${styles.shell} min-h-screen p-3 lg:p-6`}
        style={
          {
            "--workspace-sidebar-width": resolveWorkspaceSidebarWidth(isSidebarCollapsed),
          } as CSSProperties
        }
      >
        <WorkspaceSidebar
          isCollapsed={isSidebarCollapsed}
          isMobileViewport={isMobileViewport}
          items={workspaceItems}
          pathname={pathname}
          sidebarPreference={sidebarPreference}
          userName={user?.username ?? "未登录"}
          onLogout={clearSession}
          onToggle={() => setSidebarPreference(getNextSidebarPreference(sidebarPreference))}
        />
        <main className={styles.content} id="workspace-main">
          <div className={`${styles.contentInner} space-y-6`}>{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}

function WorkspaceSidebar({
  isCollapsed,
  isMobileViewport,
  items,
  onLogout,
  onToggle,
  pathname,
  sidebarPreference,
  userName,
}: Readonly<{
  isCollapsed: boolean;
  isMobileViewport: boolean;
  items: WorkspaceNavItem[];
  onLogout: () => void;
  onToggle: () => void;
  pathname: string;
  sidebarPreference: "expanded" | "collapsed";
  userName: string;
}>) {
  return (
    <aside
      aria-label="工作台导航"
      className={styles.sidebar}
      data-collapsed={isCollapsed}
    >
      <div className={styles.sidebarTop}>
        <div className={styles.brandBlock}>
          <WorkspaceSidebarBrand />
          {shouldShowWorkspaceSidebarToggle(isMobileViewport) ? (
            <WorkspaceSidebarToggle
              isCollapsed={isCollapsed}
              sidebarPreference={sidebarPreference}
              onToggle={onToggle}
            />
          ) : null}
        </div>
        <div>
          <p className={styles.sectionLabel}>主导航</p>
          <WorkspaceSidebarNav items={items} pathname={pathname} />
        </div>
      </div>
      <WorkspaceSidebarSession userName={userName} onLogout={onLogout} />
    </aside>
  );
}

function useIsMobileViewport() {
  return useSyncExternalStore(
    subscribeToMobileViewport,
    getMobileViewportSnapshot,
    getMobileViewportServerSnapshot,
  );
}

function getMobileViewportSnapshot() {
  if (typeof window === "undefined") {
    return false;
  }
  return window.matchMedia(MOBILE_VIEWPORT_MEDIA_QUERY).matches;
}

function getMobileViewportServerSnapshot() {
  return false;
}

function subscribeToMobileViewport(onStoreChange: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }
  const mediaQueryList = window.matchMedia(MOBILE_VIEWPORT_MEDIA_QUERY);
  mediaQueryList.addEventListener("change", onStoreChange);
  return () => {
    mediaQueryList.removeEventListener("change", onStoreChange);
  };
}

function WorkspaceSidebarBrand() {
  return (
    <div className={styles.brandHeader}>
      <span aria-hidden="true" className={styles.glyph}>
        <WorkspaceBrandIcon />
      </span>
      <div className={styles.brandCopy}>
        <p className={styles.brandEyebrow}>创作空间</p>
        <p className={styles.brandTitle}>工作台</p>
      </div>
    </div>
  );
}

function WorkspaceSidebarNav({ items, pathname }: Readonly<{ items: WorkspaceNavItem[]; pathname: string }>) {
  return (
    <nav aria-label="主导航" className={`${styles.nav} grid gap-2`}>
      {items.map((item) => <WorkspaceSidebarNavItem item={item} key={item.label} pathname={pathname} />)}
    </nav>
  );
}

function WorkspaceSidebarNavItem({ item, pathname }: Readonly<{ item: WorkspaceNavItem; pathname: string }>) {
  const navMeta = item.disabled ? "选择项目" : item.meta;
  const navContent = (
    <>
      <span aria-hidden="true" className={styles.glyph}>
        <WorkspaceNavIcon segment={item.segment} />
      </span>
      <span className={styles.navCopy}>
        <span className={styles.navLabel}>{item.label}</span>
        <span className={`${styles.navMeta} text-xs`}>
          {navMeta}
        </span>
      </span>
    </>
  );
  if (item.href) {
    return (
      <Link
        aria-current={isWorkspaceItemActive(item, pathname) ? "page" : undefined}
        aria-label={item.label}
        className={`ink-tab ${styles.navItem}`}
        data-active={isWorkspaceItemActive(item, pathname)}
        data-disabled={false}
        href={item.href}
        title={item.label}
      >
        {navContent}
      </Link>
    );
  }
  return (
    <button
      aria-label={item.label}
      className={`ink-tab ${styles.navItem}`}
      data-active={false}
      data-disabled
      disabled
      title={item.label}
      type="button"
    >
      {navContent}
    </button>
  );
}

function WorkspaceSidebarSession({ onLogout, userName }: Readonly<{
  onLogout: () => void;
  userName: string;
}>) {
  return (
    <div className={styles.sessionArea}>
      <div className={styles.sessionSummary}>
        <span className={`${styles.sessionBadge} font-medium`}>{resolveWorkspaceUserBadge(userName)}</span>
        <div className={styles.sessionCopy}>
          <p className={styles.sessionLabel}>当前账号</p>
          <p className={styles.sessionUser}>{userName}</p>
        </div>
      </div>
      <button
        aria-label="退出登录"
        className={`ink-button-secondary ${styles.logoutButton}`}
        onClick={onLogout}
        type="button"
      >
        <span aria-hidden="true" className={styles.glyph}>
          <WorkspaceLogoutIcon />
        </span>
        <span className={styles.logoutLabel}>退出登录</span>
      </button>
    </div>
  );
}

function WorkspaceSidebarToggle({ isCollapsed, onToggle, sidebarPreference }: Readonly<{
  isCollapsed: boolean;
  onToggle: () => void;
  sidebarPreference: "expanded" | "collapsed";
}>) {
  const label = isCollapsed ? "展开导航" : "收起导航";
  return (
    <button
      aria-label={label}
      aria-pressed={sidebarPreference === "collapsed"}
      className={`ink-button-secondary ${styles.toggleButton} shrink-0 px-3`}
      onClick={onToggle}
      title={label}
      type="button"
    >
      <span aria-hidden="true" className={styles.toggleIcon}>
        <WorkspaceToggleIcon collapsed={isCollapsed} />
      </span>
    </button>
  );
}
