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
import styles from "@/features/workspace/components/workspace-shell.module.css";

const MOBILE_VIEWPORT_MEDIA_QUERY = "(max-width: 1023px)";

export function WorkspaceShell({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
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
      <div
        className={`${styles.shell} min-h-screen gap-4 p-3 lg:gap-6 lg:p-6`}
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
        <main className={`${styles.content} space-y-6`}>{children}</main>
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
    <aside className={`${styles.sidebar} panel-shell flex flex-col gap-4 p-4 lg:justify-between lg:p-5`} data-collapsed={isCollapsed}>
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <WorkspaceSidebarBrand />
          {shouldShowWorkspaceSidebarToggle(isMobileViewport) ? (
            <WorkspaceSidebarToggle
              isCollapsed={isCollapsed}
              sidebarPreference={sidebarPreference}
              onToggle={onToggle}
            />
          ) : null}
        </div>
        <WorkspaceSidebarNav items={items} pathname={pathname} />
      </div>
      <WorkspaceSidebarSession isCollapsed={isCollapsed} userName={userName} onLogout={onLogout} />
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
    <div className="flex min-w-0 items-start gap-3">
      <span className={`${styles.glyph} mt-0.5 font-serif text-lg font-semibold`}>易</span>
      <div className={`${styles.brandCopy} min-w-0 space-y-1`}>
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--accent-ink)]">easyStory</p>
        <h1 className="font-serif text-2xl leading-tight font-semibold lg:text-3xl">水墨流工作台</h1>
        <p className={`${styles.brandDescription} text-sm leading-6 text-[var(--text-secondary)]`}>
          项目管理、内容创作、工作流控制、风格分析，一站搞定。
        </p>
      </div>
    </div>
  );
}

function WorkspaceSidebarNav({
  items,
  pathname,
}: Readonly<{
  items: WorkspaceNavItem[];
  pathname: string;
}>) {
  return (
    <nav aria-label="主导航" className={`${styles.nav} grid gap-2`}>
      {items.map((item) => <WorkspaceSidebarNavItem item={item} key={item.label} pathname={pathname} />)}
    </nav>
  );
}

function WorkspaceSidebarNavItem({
  item,
  pathname,
}: Readonly<{
  item: WorkspaceNavItem;
  pathname: string;
}>) {
  const navMeta = item.disabled ? "选择项目" : item.meta;
  const navContent = (
    <>
      <span aria-hidden="true" className={styles.glyph}>{item.shortLabel}</span>
      <span className={styles.navCopy}>
        <span className={styles.navLabel}>{item.label}</span>
        <span className={`${styles.navMeta} text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]`}>
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
      disabled
      title={item.label}
      type="button"
    >
      {navContent}
    </button>
  );
}

function WorkspaceSidebarSession({
  isCollapsed,
  onLogout,
  userName,
}: Readonly<{
  isCollapsed: boolean;
  onLogout: () => void;
  userName: string;
}>) {
  return (
    <div className={`${styles.sessionArea} space-y-3`}>
      <div className={`${styles.sessionCard} panel-muted flex items-center gap-3 p-3`}>
        <span className={`${styles.sessionBadge} font-medium`}>{resolveWorkspaceUserBadge(userName)}</span>
        <div className={`${styles.sessionCopy} min-w-0 space-y-1`}>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-secondary)]">当前会话</p>
          <p className="truncate font-medium text-[var(--text-primary)]">{userName}</p>
          <p className={`${styles.sessionDescription} text-sm leading-6 text-[var(--text-secondary)]`}>
            点击下方按钮安全退出当前账号。
          </p>
        </div>
      </div>
      <button
        aria-label="退出登录"
        className={`ink-button-secondary ${styles.logoutButton} w-full`}
        data-collapsed={isCollapsed}
        onClick={onLogout}
        type="button"
      >
        <span aria-hidden="true" className={styles.glyph}>退</span>
        <span className={styles.logoutLabel}>退出登录</span>
      </button>
    </div>
  );
}

function WorkspaceSidebarToggle({
  isCollapsed,
  onToggle,
  sidebarPreference,
}: Readonly<{
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
      <span aria-hidden="true" className={styles.toggleIcon}>{isCollapsed ? "展" : "收"}</span>
    </button>
  );
}
