"use client";

import type { ReactNode } from "react";
import Link from "next/link";

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
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
    active: true,
  },
  {
    href: "/workspace/lobby/settings?tab=assistant",
    label: "我的助手",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3c3.87 0 7 2.91 7 6.5 0 1.68-.7 3.2-1.86 4.35L18 21l-4.25-2.13c-.56.09-1.14.13-1.75.13-3.87 0-7-2.91-7-6.5S8.13 3 12 3z" />
      </svg>
    ),
  },
  {
    href: "/workspace/lobby/templates",
    label: "模板库",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    ),
  },
  {
    href: "/workspace/lobby/recycle-bin",
    label: "回收站",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 6 5 6 21 6" />
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      </svg>
    ),
  },
] as const;

export function LobbyPage() {
  const model = useLobbyProjectModel({ deletedOnly: false });
  const projectCount = model.projectsQuery.data?.length ?? 0;
  const filteredProjectCount = model.filteredProjects.length;

  return (
    <div className="-mt-4 grid min-h-[calc(100vh-72px)] [grid-template-columns:1fr] lg:[grid-template-columns:240px_minmax(0,1fr)] gap-5 lg:gap-7 items-start">
      <aside className="lg:sticky top-[5.5rem] flex flex-col gap-1 p-3 lg:p-4 max-lg:order-2 rounded-2xl border border-line-soft/60 bg-[var(--bg-glass-heavy)] backdrop-blur-sm">
        <nav className="flex flex-row lg:flex-col gap-1 overflow-x-auto scrollbar-hide max-lg:-mx-1 max-lg:px-1">
          {LOBBY_NAV_ITEMS.map((item) => (
            <LobbySidebarLink item={item} key={item.href} />
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-2 pt-3 max-lg:hidden">
          <Link
            className="flex items-center justify-center gap-1.5 rounded-2xl border border-dashed border-border px-4 py-2.5 text-[0.84rem] text-text-secondary transition-colors hover:bg-accent-soft hover:text-accent-primary"
            href="/workspace/lobby/settings?tab=assistant"
          >
            打开我的助手
          </Link>
          {model.templatePreviewNames.length > 0 && (
            <p className="text-text-tertiary text-[0.78rem] leading-relaxed px-1">
              当前节奏：{model.templatePreviewNames.join(" · ")}
            </p>
          )}
        </div>
      </aside>

      <main className="grid gap-5 min-w-0 max-lg:order-1">
        <div className="flex flex-wrap gap-3 items-center max-lg:flex-col max-lg:stretch">
          <input
            className="ink-input-roomy min-h-12 flex-1 max-lg:w-full text-[0.95rem]"
            placeholder="搜索作品名、题材或模板…"
            value={model.searchText}
            onChange={(event) => model.setSearchText(event.target.value)}
          />
          <Link className="ink-button whitespace-nowrap max-lg:w-full max-lg:text-center" href="/workspace/lobby/new">
            新建作品
          </Link>
        </div>

        <p className="text-text-tertiary text-[0.84rem]">
          {model.searchText
            ? `筛选出 ${filteredProjectCount} 部作品`
            : `共 ${projectCount} 部作品`}
        </p>

        <LobbyProjectShelf
          actionMutation={model.actionMutation}
          deletedOnly={false}
          error={model.projectsQuery.error}
          isLoading={model.projectsQuery.isLoading}
          projects={model.filteredProjects}
          templateNameById={model.templateNameById}
        />
      </main>
    </div>
  );
}

function LobbySidebarLink({ item }: Readonly<{ item: LobbyNavItem }>) {
  return (
    <Link
      className={`relative grid [grid-template-columns:auto_minmax(0,1fr)] gap-2.5 items-start p-2.5 pl-3 rounded-2xl transition-all duration-fast hover:bg-surface-hover hover:translate-x-[2px] whitespace-nowrap lg:whitespace-normal ${item.active ? "bg-accent-soft before:content-[''] before:absolute before:top-2.5 before:bottom-2.5 before:left-1.5 before:w-[2.5px] before:rounded-full before:bg-accent-primary max-lg:before:hidden" : ""}`}
      href={item.href}
    >
      <span aria-hidden="true" className="inline-flex w-8 h-8 items-center justify-center rounded-2xl bg-accent-soft text-accent-primary">
        <span className="w-4 h-4">{item.icon}</span>
      </span>
      <span className="grid min-w-0">
        <span className="text-text-primary text-[0.95rem] font-semibold tracking-[-0.02em]">{item.label}</span>
      </span>
    </Link>
  );
}

