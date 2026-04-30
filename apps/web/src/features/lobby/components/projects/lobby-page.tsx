"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { LobbyProjectShelf } from "@/features/lobby/components/projects/lobby-project-shelf";
import { useLobbyProjectModel } from "@/features/lobby/components/projects/lobby-project-model";
import { BinIcon, GearIcon, GridIcon, ScrollIcon } from "@/components/icons/shared-icons";

export function LobbyPage() {
  const model = useLobbyProjectModel({ deletedOnly: false });
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [hoveredNav, setHoveredNav] = useState<string | null>(null);

  useEffect(() => {
    queueMicrotask(() => setMounted(true));
  }, []);

  const navItems = [
    { id: "works", icon: ScrollIcon, label: "作品", href: "/workspace/lobby", active: true },
    { id: "templates", icon: GridIcon, label: "模板", href: "/workspace/lobby/templates" },
    { id: "bin", icon: BinIcon, label: "回收", href: "/workspace/lobby/recycle-bin" },
    { id: "settings", icon: GearIcon, label: "设置", href: "/workspace/lobby/settings" },
  ];

  return (
    <div
      className="relative min-h-screen flex bg-canvas"
    >
      {/* 左侧图标边栏 — 无边框，用阴影区分层级 */}
      <aside
        className="fixed left-0 top-0 h-screen w-16 flex flex-col items-center py-6 z-30 hidden lg:flex"
        style={{
          background: "var(--bg-surface)",
          boxShadow: "var(--shadow-panel-side)",
        }}
      >
        {/* Logo */}
        <Link href="/" className="mb-10">
          <span
            className="inline-flex items-center justify-center w-9 h-9 rounded-lg text-[11px] font-semibold tracking-[0.12em]"
            style={{
              background: "linear-gradient(135deg, var(--accent-primary), var(--accent-primary-dark))",
              color: "var(--text-on-accent)",
            }}
          >
            ES
          </span>
        </Link>

        {/* 导航图标 */}
        <nav className="flex flex-col gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isHovered = hoveredNav === item.id;
            return (
              <div
                key={item.id}
                className="relative"
                onMouseEnter={() => setHoveredNav(item.id)}
                onMouseLeave={() => setHoveredNav(null)}
              >
                <Link
                  href={item.href}
                  className="flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-200"
                  style={{
                    background: item.active ? "var(--accent-primary-soft)" : isHovered ? "var(--bg-muted)" : "transparent",
                    color: item.active ? "var(--accent-primary)" : "var(--text-tertiary)",
                  }}
                >
                  <Icon className="w-[18px] h-[18px]" />
                </Link>
                {/* 悬停提示 */}
                {isHovered && (
                  <div
                    className="absolute left-12 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-lg text-[12px] font-medium whitespace-nowrap z-50"
                    style={{
                      background: "var(--bg-glass-heavy)",
                      backdropFilter: "blur(12px)",
                      color: "var(--text-primary)",
                      border: "1px solid var(--line-soft)",
                      boxShadow: "var(--shadow-md)",
                    }}
                  >
                    {item.label}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* 底部用户 */}
        <div className="mt-auto">
          <button
            className="flex items-center justify-center w-10 h-10 rounded-xl text-text-tertiary"
            onClick={() => {
              router.push("/auth/login");
            }}
          >
            <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
          </button>
        </div>
      </aside>

      {/* 主内容 */}
      <main className="flex-1 lg:ml-16 min-w-0">
        {/* 页面标题区 — 非 sticky，因为上面已有全局导航 */}
        <header
          className="flex items-center justify-between px-6 py-5"
          style={{
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(-8px)",
            transition: "all 0.8s ease 0.2s",
          }}
        >
          <div>
            <h1
              className="font-serif text-[22px] font-semibold tracking-[-0.02em] text-text-primary"
            >
              书架
            </h1>
            <p
              className="mt-0.5 text-[13px] text-text-tertiary"
            >
              {model.projectsQuery.data?.length ?? 0} 部作品
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* 搜索 */}
            <div
              className="relative hidden sm:block"
              style={{
                opacity: mounted ? 1 : 0,
                transition: "opacity 0.8s ease 0.4s",
              }}
            >
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                style={{ color: "var(--text-tertiary)" }}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <input
                className="ink-input-roomy min-h-9 w-[200px] pl-9 text-[13px]"
                placeholder="搜索作品…"
                value={model.searchText}
                onChange={(e) => model.setSearchText(e.target.value)}
              />
            </div>

            {/* 新建 */}
            <Link
              href="/workspace/lobby/new"
              className="ink-button-hero text-[13px] min-h-9 px-4"
              style={{
                opacity: mounted ? 1 : 0,
                transform: mounted ? "scale(1)" : "scale(0.9)",
                transition: "all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) 0.5s",
              }}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
              新建
            </Link>
          </div>
        </header>

        {/* 项目区域 */}
        <div
          className="px-6 pb-12"
          style={{
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(12px)",
            transition: "all 1s ease 0.4s",
          }}
        >
          <LobbyProjectShelf
            actionMutation={model.actionMutation}
            deletedOnly={false}
            error={model.projectsQuery.error}
            isLoading={model.projectsQuery.isLoading}
            projects={model.filteredProjects}
            templateNameById={model.templateNameById}
            viewMode="grid"
          />
        </div>
      </main>
    </div>
  );
}
