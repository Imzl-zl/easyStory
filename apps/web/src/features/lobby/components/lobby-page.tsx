"use client";

import type { ReactNode } from "react";
import Link from "next/link";

import { LobbyProjectShelf } from "@/features/lobby/components/lobby-project-shelf";
import { useLobbyProjectModel } from "@/features/lobby/components/lobby-project-model";
import styles from "./lobby-page.module.css";

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
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarIntro}>
          <p className={styles.sidebarEyebrow}>书架</p>
          <h2 className={styles.sidebarTitle}>作品空间</h2>
          <p className={styles.sidebarDescription}>把项目、模板和助手放在同一张写作桌面上，而不是拆成后台模块。</p>
        </div>
        <nav className={styles.sidebarNav}>
          {LOBBY_NAV_ITEMS.map((item) => (
            <LobbySidebarLink item={item} key={item.href} />
          ))}
        </nav>
        <div className={styles.sidebarNote}>
          <p className={styles.sidebarNoteTitle}>当前节奏</p>
          <p className={styles.sidebarNoteBody}>{helperText}</p>
        </div>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <div className={styles.headerInfo}>
            <p className={styles.eyebrow}>继续创作</p>
            <h1 className={styles.title}>从书架回到故事现场</h1>
            <p className={styles.subtitle}>打开项目就进入创作路径。规则、Skills、模型连接和工具都应该贴着作品工作，而不是先去管理页里翻找。</p>
          </div>
          <div className={styles.headerActions}>
            <Link className="ink-button-secondary" href="/workspace/lobby/settings?tab=assistant">
              打开我的助手
            </Link>
            <Link className="ink-button" href="/workspace/lobby/new">
              新建作品
            </Link>
          </div>
        </header>

        <section className={styles.shelfBar}>
          <label className={styles.searchField}>
            <span className={styles.searchLabel}>搜索作品</span>
            <input
              className={styles.searchInput}
              placeholder="搜索作品名、题材或模板…"
              value={model.searchText}
              onChange={(event) => model.setSearchText(event.target.value)}
            />
          </label>
          <div className={styles.metrics}>
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
    <Link className={styles.sidebarLink} data-active={item.active ? "true" : "false"} href={item.href}>
      <span aria-hidden="true" className={styles.sidebarIcon}>
        {item.icon}
      </span>
      <span className={styles.sidebarCopy}>
        <span className={styles.sidebarLinkLabel}>{item.label}</span>
        <span className={styles.sidebarLinkMeta}>{item.description}</span>
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
    <div className={styles.metricCard}>
      <span className={styles.metricLabel}>{label}</span>
      <strong className={styles.metricValue}>{new Intl.NumberFormat("zh-CN").format(value)}</strong>
    </div>
  );
}
