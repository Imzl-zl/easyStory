"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

const PROJECT_PATH_PATTERN = /^\/workspace\/project\/([^/]+)\//;
const PROJECT_SETTINGS_PATH_PATTERN = /^\/workspace\/project\/[^/]+\/settings(?:\/|$)/;
const LOBBY_PATH_PREFIX = "/workspace/lobby";
const PROJECT_WORKSPACE_ITEMS = [
  { segment: "studio", label: "Studio" },
  { segment: "engine", label: "Engine" },
  { segment: "lab", label: "Lab" },
];

export function WorkspaceShell({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const lastProjectId = useWorkspaceStore((state) => state.lastProjectId);
  const setLastProjectId = useWorkspaceStore((state) => state.setLastProjectId);
  const currentProjectId = useMemo(() => pathname.match(PROJECT_PATH_PATTERN)?.[1] ?? null, [pathname]);
  const workspaceItems = useMemo(() => {
    const projectId = currentProjectId ?? lastProjectId;
    return [
      { href: "/workspace/lobby", label: "Lobby", segment: "lobby", disabled: false },
      ...PROJECT_WORKSPACE_ITEMS.map((item) => ({
        href: projectId ? `/workspace/project/${projectId}/${item.segment}` : null,
        label: item.label,
        segment: item.segment,
        disabled: projectId === null,
      })),
    ];
  }, [currentProjectId, lastProjectId]);

  useEffect(() => {
    if (currentProjectId) {
      setLastProjectId(currentProjectId);
    }
  }, [currentProjectId, setLastProjectId]);

  return (
    <AuthGuard>
      <div className="grid min-h-screen gap-6 p-4 lg:grid-cols-[260px_1fr] lg:p-6">
        <aside className="panel-shell flex flex-col justify-between p-5">
          <div className="space-y-8">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.3em] text-[var(--accent-ink)]">
                easyStory
              </p>
              <h1 className="font-serif text-3xl leading-tight font-semibold">水墨流工作台</h1>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
                Web 版工作台，固定 `Lobby / Studio / Engine / Lab` 四柱结构。
              </p>
            </div>

            <nav className="space-y-2" aria-label="主导航">
              {workspaceItems.map((item) => {
                const isActive = isWorkspaceItemActive(item.segment, item.href, pathname);
                return (
                  item.href ? (
                    <Link
                      key={item.label}
                      className="ink-tab w-full justify-between"
                      data-active={isActive}
                      href={item.href}
                    >
                      <span>{item.label}</span>
                      <span className="text-xs uppercase tracking-[0.18em]">
                        {item.label === "Lobby" ? "Projects" : "Project"}
                      </span>
                    </Link>
                  ) : (
                    <button
                      key={item.label}
                      className="ink-tab w-full justify-between"
                      data-active={false}
                      disabled
                      type="button"
                    >
                      <span>{item.label}</span>
                      <span className="text-xs uppercase tracking-[0.18em]">选择</span>
                    </button>
                  )
                );
              })}
            </nav>
          </div>

          <div className="space-y-4">
            <div className="panel-muted p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-secondary)]">
                当前会话
              </p>
              <p className="mt-2 font-medium">{user?.username ?? "未登录"}</p>
              <p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">
                前端默认直连 FastAPI，未启用静默 mock。
              </p>
            </div>
            <button className="ink-button-secondary w-full" onClick={() => clearSession()}>
              退出登录
            </button>
          </div>
        </aside>

        <main className="space-y-6">{children}</main>
      </div>
    </AuthGuard>
  );
}

function isWorkspaceItemActive(segment: string, href: string | null, pathname: string) {
  if (!href) {
    return false;
  }
  if (segment === "lobby") {
    return pathname.startsWith(LOBBY_PATH_PREFIX);
  }
  if (segment === "studio" && PROJECT_SETTINGS_PATH_PATTERN.test(pathname)) {
    return true;
  }
  return pathname.includes(`/${segment}`);
}
