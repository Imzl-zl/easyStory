"use client";

import type { ReactNode } from "react";
import Link from "next/link";

import { LobbyProjectShelf } from "@/features/lobby/components/lobby-project-shelf";
import { useLobbyProjectModel } from "@/features/lobby/components/lobby-project-model";

type LobbyNavItem = {
  description: string;
  href: string;
  icon: ReactNode;
  label: string;
  active?: boolean;
};

const LOBBY_NAV_ITEMS: ReadonlyArray<LobbyNavItem> = [
  {
    href: "/workspace/lobby",
    label: "我的作品",
    description: "从书架继续进入正在写的故事。",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
    active: true,
  },
  {
    href: "/workspace/lobby/settings?tab=assistant",
    label: "我的助手",
    description: "规则、Skills、模型连接和工具都在这里直接生效。",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 3c3.87 0 7 2.91 7 6.5 0 1.68-.7 3.2-1.86 4.35L18 21l-4.25-2.13c-.56.09-1.14.13-1.75.13-3.87 0-7-2.91-7-6.5S8.13 3 12 3z" />
      </svg>
    ),
  },
  {
    href: "/workspace/lobby/templates",
    label: "模板库",
    description: "用题材模板快速开始，不重新做一遍项目初始化。",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    ),
  },
  {
    href: "/workspace/lobby/recycle-bin",
    label: "回收站",
    description: "暂时搁置的项目还在，随时恢复。",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
  const helperText = model.templatePreviewNames.length > 0
    ? `最近常用模板：${model.templatePreviewNames.join(" · ")}`
    : "先从一个故事开始，助手和模板会跟着作品一起工作。";

  return (
    <div className="grid min-h-[calc(100vh-72px)] [grid-template-columns:272px_minmax(0,1fr)] gap-7 items-start">
      <aside className="sticky top-[5.5rem] flex flex-col gap-3 p-[1.4rem_1.1rem] rounded-[28px] bg-[linear-gradient(180deg,rgba(255,255,255,0.62),rgba(255,255,255,0.28)),var(--bg-muted)] shadow-[inset_0_0_0_1px_rgba(61,61,61,0.06)]">
        <div className="grid gap-[0.55rem] p-[0.2rem_0.35rem_0]">
          <p className="text-[var(--text-tertiary)] text-[0.68rem] font-semibold tracking-[0.14em] uppercase">书架</p>
          <h2 className="text-[var(--text-primary)] font-serif text-[1.55rem] font-semibold tracking-[-0.04em]">作品空间</h2>
          <p className="text-[var(--text-secondary)] text-[0.9rem] leading-relaxed">把项目、模板和助手放在同一张写作桌面上，而不是拆成后台模块。</p>
        </div>
        <nav className="flex flex-col gap-[0.55rem]">
          {LOBBY_NAV_ITEMS.map((item) => (
            <LobbySidebarLink item={item} key={item.href} />
          ))}
        </nav>
        <div className="grid gap-[0.45rem] p-4 pb-[1.05rem] rounded-5 bg-[rgba(255,255,255,0.58)]">
          <p className="text-[var(--text-tertiary)] text-[0.68rem] font-semibold tracking-[0.14em] uppercase">当前节奏</p>
          <p className="text-[var(--text-secondary)] text-[0.84rem] leading-relaxed">{helperText}</p>
        </div>
      </aside>

      <main className="grid gap-6 min-w-0">
        <header className="grid [grid-template-columns:minmax(0,1fr)_auto] gap-4 items-end p-[0.35rem_0_0.25rem]">
          <div className="grid gap-2 min-w-0">
            <p className="text-[var(--text-tertiary)] text-[0.68rem] font-semibold tracking-[0.14em] uppercase">继续创作</p>
            <h1 className="text-[var(--text-primary)] font-serif text-[clamp(2.1rem,4vw,3.4rem)] font-semibold tracking-[-0.05em] leading-tight">从书架回到故事现场</h1>
            <p className="max-w-[60rem] text-[var(--text-secondary)] text-base leading-relaxed">打开项目就进入创作路径。规则、Skills、模型连接和工具都应该贴着作品工作，而不是先去管理页里翻找。</p>
          </div>
          <div className="flex flex-wrap gap-[0.6rem] items-center justify-end">
            <Link className="ink-button-secondary" href="/workspace/lobby/settings?tab=assistant">
              打开我的助手
            </Link>
            <Link className="ink-button" href="/workspace/lobby/new">
              新建作品
            </Link>
          </div>
        </header>

        <section className="grid [grid-template-columns:minmax(0,1fr)_auto] gap-4 items-stretch p-4 px-[1.1rem] rounded-[26px] bg-[rgba(255,255,255,0.58)] shadow-[inset_0_0_0_1px_rgba(61,61,61,0.06)]">
          <label className="grid gap-[0.55rem] min-w-0">
            <span className="text-[var(--text-tertiary)] text-[0.68rem] font-semibold tracking-[0.14em] uppercase">搜索作品</span>
            <input
              className="w-full min-h-12 px-4 border border-[rgba(61,61,61,0.08)] rounded-[18px] bg-[rgba(255,255,255,0.86)] text-[var(--text-primary)] text-[0.95rem] transition-all hover:border-[var(--line-strong)] focus:border-[var(--accent-primary)] focus:shadow-[0_0_0_3px_rgba(90,122,107,0.12)] focus:outline-none placeholder:text-[var(--text-placeholder)]"
              placeholder="搜索作品名、题材或模板…"
              value={model.searchText}
              onChange={(event) => model.setSearchText(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-3 items-stretch justify-end">
            <LobbyMetric label="当前作品" value={projectCount} />
            <LobbyMetric label="筛选结果" value={filteredProjectCount} />
            <LobbyMetric label="模板库" value={model.templateCount} />
          </div>
        </section>

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
    <Link className={`relative grid [grid-template-columns:auto_minmax(0,1fr)] gap-2 items-start p-[0.95rem_0.95rem_0.95rem_1rem] rounded-[22px] bg-transparent transition-all hover:bg-[rgba(255,255,255,0.48)] hover:translate-x-[2px] ${item.active ? "bg-[rgba(255,255,255,0.74)] before:content-[''] before:absolute before:top-[0.95rem] before:bottom-[0.95rem] before:left-[0.4rem] before:w-[2px] before:rounded-full before:bg-[var(--accent-primary)]" : ""}`} href={item.href}>
      <span aria-hidden="true" className="inline-flex w-8 h-8 items-center justify-center rounded-3.5 bg-[rgba(90,122,107,0.08)] text-[var(--accent-primary)]">
        <span className="w-4 h-4">{item.icon}</span>
      </span>
      <span className="grid gap-[0.22rem] min-w-0">
        <span className="text-[var(--text-primary)] text-[0.95rem] font-semibold tracking-[-0.02em]">{item.label}</span>
        <span className="text-[var(--text-secondary)] text-[0.8rem] leading-relaxed">{item.description}</span>
      </span>
    </Link>
  );
}

function LobbyMetric({
  label,
  value,
}: Readonly<{
  label: string;
  value: number;
}>) {
  return (
    <div className="grid min-w-[118px] gap-[0.35rem] p-[0.9rem_1rem] rounded-5 bg-[rgba(248,246,241,0.88)]">
      <span className="text-[var(--text-tertiary)] text-[0.68rem] font-semibold tracking-[0.14em] uppercase">{label}</span>
      <strong className="text-[var(--text-primary)] text-[1.3rem] font-semibold [font-variant-numeric:tabular-nums] tracking-[-0.03em]">{new Intl.NumberFormat("zh-CN").format(value)}</strong>
    </div>
  );
}
