"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useState } from "react";

import { LobbyProjectShelf } from "@/features/lobby/components/projects/lobby-project-shelf";
import { useLobbyProjectModel } from "@/features/lobby/components/projects/lobby-project-model";

type LobbyNavItem = {
  href: string;
  icon: ReactNode;
  label: string;
  active?: boolean;
};

const LOBBY_NAV_ITEMS: ReadonlyArray<LobbyNavItem> = [
  {
    href: "/workspace/lobby",
    label: "我的作品",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    ),
    active: true,
  },
  {
    href: "/workspace/lobby/settings?tab=assistant",
    label: "我的助手",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 6.34L2.1 2.1m17.8 17.8l-4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.07-4.93l-4.24 4.24M6.34 6.34l-4.24-4.24" />
      </svg>
    ),
  },
  {
    href: "/workspace/lobby/templates",
    label: "模板库",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M3 9h18M9 21V9" />
      </svg>
    ),
  },
  {
    href: "/workspace/lobby/recycle-bin",
    label: "回收站",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      </svg>
    ),
  },
] as const;

export function LobbyPage() {
  const model = useLobbyProjectModel({ deletedOnly: false });
  const projectCount = model.projectsQuery.data?.length ?? 0;
  const filteredProjectCount = model.filteredProjects.length;
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  return (
    <div className="grid min-h-[calc(100vh-72px)] [grid-template-columns:1fr] lg:[grid-template-columns:220px_minmax(0,1fr)] gap-0">
      {/* 左侧导航书架 */}
      <aside className="lg:sticky lg:top-[4.5rem] lg:h-[calc(100vh-4.5rem)] flex flex-col border-r border-line-soft/40 bg-[var(--bg-surface-warm-gradient)]">
        <div className="flex flex-col gap-0.5 p-3 lg:p-4">
          <div className="mb-4 px-3 max-lg:hidden">
            <span className="label-overline">工作台</span>
          </div>
          <nav className="flex flex-row lg:flex-col gap-1 overflow-x-auto scrollbar-hide max-lg:-mx-1 max-lg:px-1">
            {LOBBY_NAV_ITEMS.map((item) => (
              <LobbySidebarLink item={item} key={item.href} />
            ))}
          </nav>
        </div>

        <div className="mt-auto p-4 max-lg:hidden">
          <div className="rounded-2xl border border-dashed border-line-strong/40 p-4 space-y-3">
            <div className="flex items-center gap-2 text-text-secondary">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M12 5v14M5 12h14" />
              </svg>
              <span className="text-[0.82rem] font-medium">快速开始</span>
            </div>
            <Link
              className="flex items-center justify-center gap-1.5 rounded-xl bg-accent-primary px-4 py-2.5 text-[0.84rem] font-medium text-text-on-accent transition-all hover:bg-accent-primary-hover hover:shadow-md active:scale-[0.97]"
              href="/workspace/lobby/new"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              新建作品
            </Link>
            {model.templatePreviewNames.length > 0 && (
              <p className="text-text-tertiary text-[0.75rem] leading-relaxed">
                常用：{model.templatePreviewNames.join(" · ")}
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="min-w-0">
        {/* 顶部工具栏 */}
        <div className="sticky top-0 z-10 border-b border-line-soft/40 bg-glass-heavy/90 backdrop-blur-xl">
          <div className="flex flex-wrap items-center gap-3 px-5 py-3.5">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <h1 className="text-text-primary text-[1.1rem] font-semibold tracking-[-0.02em] whitespace-nowrap">
                我的作品
              </h1>
              <span className="inline-flex items-center h-5 px-2 rounded-full bg-muted text-text-tertiary text-[0.72rem] font-medium">
                {model.searchText ? filteredProjectCount : projectCount}
              </span>
            </div>

            <div className="flex items-center gap-2">
              {/* 搜索 */}
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.35-4.35" />
                </svg>
                <input
                  className="ink-input-roomy min-h-10 w-[200px] lg:w-[280px] pl-9 text-[0.9rem]"
                  placeholder="搜索作品…"
                  value={model.searchText}
                  onChange={(event) => model.setSearchText(event.target.value)}
                />
              </div>

              {/* 视图切换 */}
              <div className="hidden sm:flex items-center rounded-xl bg-muted p-0.5">
                <button
                  className={`inline-flex items-center justify-center w-8 h-8 rounded-lg transition-all ${viewMode === "grid" ? "bg-elevated shadow-sm text-accent-primary" : "text-text-tertiary hover:text-text-secondary"}`}
                  onClick={() => setViewMode("grid")}
                  type="button"
                  title="网格视图"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <rect x="3" y="3" width="7" height="7" rx="1" />
                    <rect x="14" y="3" width="7" height="7" rx="1" />
                    <rect x="3" y="14" width="7" height="7" rx="1" />
                    <rect x="14" y="14" width="7" height="7" rx="1" />
                  </svg>
                </button>
                <button
                  className={`inline-flex items-center justify-center w-8 h-8 rounded-lg transition-all ${viewMode === "list" ? "bg-elevated shadow-sm text-accent-primary" : "text-text-tertiary hover:text-text-secondary"}`}
                  onClick={() => setViewMode("list")}
                  type="button"
                  title="列表视图"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
                  </svg>
                </button>
              </div>

              {/* 新建按钮（桌面端） */}
              <Link
                className="ink-button hidden lg:inline-flex"
                href="/workspace/lobby/new"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                新建
              </Link>
            </div>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="p-5 pb-8">
          {model.searchText && (
            <p className="mb-4 text-text-tertiary text-[0.84rem]">
              筛选结果：{filteredProjectCount} 部作品
            </p>
          )}

          <LobbyProjectShelf
            actionMutation={model.actionMutation}
            deletedOnly={false}
            error={model.projectsQuery.error}
            isLoading={model.projectsQuery.isLoading}
            projects={model.filteredProjects}
            templateNameById={model.templateNameById}
            viewMode={viewMode}
          />
        </div>
      </main>
    </div>
  );
}

function LobbySidebarLink({ item }: Readonly<{ item: LobbyNavItem }>) {
  return (
    <Link
      className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-fast whitespace-nowrap lg:whitespace-normal
        ${item.active 
          ? "bg-accent-primary-soft text-accent-primary" 
          : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
        }`}
      href={item.href}
    >
      <span className={`inline-flex w-5 h-5 items-center justify-center shrink-0 transition-colors ${item.active ? "text-accent-primary" : "text-text-tertiary group-hover:text-text-secondary"}`}>
        {item.icon}
      </span>
      <span className="text-[0.92rem] font-medium">{item.label}</span>
      {item.active && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2 w-1 h-1 rounded-full bg-accent-primary" />
      )}
    </Link>
  );
}
