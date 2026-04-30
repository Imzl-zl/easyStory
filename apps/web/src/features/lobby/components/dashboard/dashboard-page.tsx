"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";

import { LobbyProjectShelf } from "@/features/lobby/components/projects/lobby-project-shelf";
import { useLobbyProjectModel } from "@/features/lobby/components/projects/lobby-project-model";
import { useAuthStore } from "@/lib/stores/auth-store";
import { resolveProjectCardTone } from "@/features/lobby/components/projects/lobby-project-support";
import { useMounted } from "@/lib/hooks/use-mounted";
import { useParticleCanvas } from "@/lib/hooks/use-particle-canvas";
import { QuillIcon, ScrollIcon } from "@/components/icons/shared-icons";
import type { ProjectSummary } from "@/lib/api/types";

export function DashboardPage() {
  const model = useLobbyProjectModel({ deletedOnly: false });
  const mounted = useMounted();
  const user = useAuthStore((state) => state.user);

  const recentProjects = useMemo(
    () => (model.projectsQuery.data ?? []).slice(0, 4),
    [model.projectsQuery.data],
  );

  const totalProjects = model.projectsQuery.data?.length ?? 0;

  return (
    <div className="relative min-h-[calc(100vh-72px)] overflow-hidden">
      {/* 背景氛围层 */}
      <DashboardAtmosphere mounted={mounted} />

      <div className="relative z-10 max-w-[1440px] mx-auto px-4 sm:px-5 md:px-8 py-6 md:py-8 space-y-8 min-w-0">
        {/* 首屏：欢迎 + 快速创作 */}
        <WelcomeSection
          mounted={mounted}
          recentProjects={recentProjects}
          totalProjects={totalProjects}
          username={user?.username ?? "创作者"}
        />

        {/* 最近项目横向滚动带 */}
        {recentProjects.length > 0 && (
          <RecentProjectsStrip
            mounted={mounted}
            projects={recentProjects}
          />
        )}

        {/* 全部作品网格 */}
        <section
          style={{
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(20px)",
            transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 0.6s",
          }}
        >
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-5">
            <div>
              <h2 className="font-serif text-lg sm:text-xl font-semibold tracking-[-0.02em] text-text-primary">
                全部作品
              </h2>
              <p className="mt-0.5 text-[13px] text-text-tertiary">
                {totalProjects} 部作品在创作中
              </p>
            </div>
            <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 sm:gap-3 w-full sm:w-auto">
              <div className="relative w-full sm:w-auto">
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
                  className="ink-input-roomy min-h-9 w-full sm:w-[200px] pl-9 text-[13px]"
                  placeholder="搜索作品…"
                  value={model.searchText}
                  onChange={(e) => model.setSearchText(e.target.value)}
                />
              </div>
              <Link
                href="/workspace/lobby"
                className="ink-button-hero text-[13px] min-h-9 px-4 sm:px-5 shrink-0"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                新建
              </Link>
            </div>
          </div>

          <div className="w-full overflow-x-auto scrollbar-hide">
            <div className="min-w-full">
              <LobbyProjectShelf
                actionMutation={model.actionMutation}
                deletedOnly={false}
                error={model.projectsQuery.error}
                isLoading={model.projectsQuery.isLoading}
                projects={model.filteredProjects}
                viewMode="grid"
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

/* ============================================================
   WelcomeSection — 欢迎区 + 快速创作入口
   ============================================================ */

function WelcomeSection({
  mounted,
  recentProjects,
  totalProjects,
  username,
}: Readonly<{
  mounted: boolean;
  recentProjects: ProjectSummary[];
  totalProjects: number;
  username: string;
}>) {
  const greeting = useGreeting();
  const [hoveredQuickAction, setHoveredQuickAction] = useState<string | null>(null);

  const quickActions = [
    {
      id: "new",
      label: "开始新故事",
      description: "从空白页或 AI 对话开始",
      href: "/workspace/lobby",
      icon: QuillIcon,
      tone: "primary" as const,
    },
    {
      id: "continue",
      label: "继续创作",
      description: recentProjects.length > 0
        ? `上次在「${recentProjects[0].name}」`
        : "打开最近的项目",
      href: recentProjects.length > 0
        ? `/workspace/project/${recentProjects[0].id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`
        : "/workspace/lobby",
      icon: ScrollIcon,
      tone: "secondary" as const,
    },
  ];

  return (
    <section
      className="relative overflow-hidden rounded-[28px]"
      style={{
        background: "linear-gradient(145deg, rgba(38,43,52,0.95) 0%, rgba(30,33,41,0.92) 50%, rgba(24,27,33,0.95) 100%)",
        border: "1px solid rgba(160, 150, 130, 0.08)",
        boxShadow: "0 24px 64px rgba(15, 17, 21, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
        opacity: mounted ? 1 : 0,
        transform: mounted ? "translateY(0)" : "translateY(24px)",
        transition: "all 1.2s cubic-bezier(0.4, 0, 0.2, 1) 0.1s",
      }}
    >
      {/* 顶部光晕装饰 */}
      <div
        className="absolute top-0 left-1/4 w-96 h-48 rounded-full blur-3xl pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(160,150,130,0.06) 0%, transparent 70%)",
          opacity: mounted ? 1 : 0,
          transition: "opacity 2s ease 0.5s",
        }}
      />

      <div className="relative z-10 px-6 md:px-10 py-8 md:py-10">
        {/* 问候语 */}
        <div
          style={{
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(12px)",
            transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 0.2s",
          }}
        >
          <span
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[12px] font-medium tracking-[0.06em]"
            style={{
              background: "var(--accent-primary-soft)",
              color: "var(--accent-primary)",
              border: "1px solid var(--accent-primary-muted)",
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--accent-primary)" }} />
            {greeting.timeLabel}
          </span>

          <h1 className="mt-5 font-serif text-[clamp(1.8rem,4vw,3rem)] font-semibold leading-[1.1] tracking-[-0.03em] text-text-primary">
            {greeting.text}，
            <br />
            <span className="text-[0.85em]" style={{ color: "var(--text-secondary)" }}>
              {username}
            </span>
          </h1>

          <p className="mt-3 text-[15px] leading-relaxed max-w-lg" style={{ color: "var(--text-secondary)" }}>
            {totalProjects === 0
              ? "准备好开始你的第一个故事了吗？"
              : `你正在创作 ${totalProjects} 个故事，今天想从哪里继续？`}
          </p>
        </div>

        {/* 快速操作卡片 */}
        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quickActions.map((action, index) => {
            const isHovered = hoveredQuickAction === action.id;
            const Icon = action.icon;
            return (
              <Link
                key={action.id}
                href={action.href}
                className="group relative overflow-hidden rounded-2xl p-5 transition-all duration-300"
                onMouseEnter={() => setHoveredQuickAction(action.id)}
                onMouseLeave={() => setHoveredQuickAction(null)}
                style={{
                  background: isHovered
                    ? action.tone === "primary"
                      ? "linear-gradient(135deg, rgba(160,150,130,0.12), rgba(160,150,130,0.04))"
                      : "var(--bg-muted)"
                    : "rgba(30, 33, 41, 0.6)",
                  border: `1px solid ${isHovered ? (action.tone === "primary" ? "rgba(160,150,130,0.22)" : "var(--line-medium)") : "rgba(160,150,130,0.05)"}`,
                  opacity: mounted ? 1 : 0,
                  transform: mounted ? "translateY(0)" : "translateY(16px)",
                  transition: `all 0.8s cubic-bezier(0.4, 0, 0.2, 1) ${0.35 + index * 0.1}s`,
                }}
              >
                {/* 悬停时的背景扩散 */}
                <div
                  className="absolute inset-0 rounded-2xl transition-opacity duration-500"
                  style={{
                    background: action.tone === "primary"
                      ? "radial-gradient(circle at 80% 20%, rgba(160,150,130,0.08) 0%, transparent 60%)"
                      : "radial-gradient(circle at 80% 20%, rgba(255,255,255,0.02) 0%, transparent 60%)",
                    opacity: isHovered ? 1 : 0,
                  }}
                />

                <div className="relative z-10">
                  <div
                    className="inline-flex items-center justify-center w-10 h-10 rounded-xl mb-4 transition-all duration-300"
                    style={{
                      background: action.tone === "primary"
                        ? isHovered ? "var(--accent-primary)" : "var(--accent-primary-soft)"
                        : isHovered ? "var(--bg-elevated)" : "var(--bg-muted)",
                      color: action.tone === "primary"
                        ? isHovered ? "var(--text-on-accent)" : "var(--accent-primary)"
                        : "var(--text-secondary)",
                      transform: isHovered ? "scale(1.05)" : "scale(1)",
                    }}
                  >
                    <Icon className="w-5 h-5" />
                  </div>

                  <h3 className="font-serif text-[15px] font-semibold tracking-[-0.01em] text-text-primary">
                    {action.label}
                  </h3>
                  <p className="mt-1 text-[13px] leading-relaxed" style={{ color: "var(--text-tertiary)" }}>
                    {action.description}
                  </p>

                  <div className="mt-4 flex items-center gap-1.5 text-[12px] font-medium" style={{ color: "var(--accent-primary)" }}>
                    <span>进入</span>
                    <svg
                      className="w-3.5 h-3.5 transition-transform duration-300"
                      style={{ transform: isHovered ? "translateX(3px)" : "translateX(0)" }}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    >
                      <path d="M5 12h14" />
                      <path d="m12 5 7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   RecentProjectsStrip — 最近项目横向流
   ============================================================ */

function RecentProjectsStrip({
  mounted,
  projects,
}: Readonly<{
  mounted: boolean;
  projects: ProjectSummary[];
}>) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <section
      style={{
        opacity: mounted ? 1 : 0,
        transform: mounted ? "translateY(0)" : "translateY(20px)",
        transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 0.4s",
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="font-serif text-lg font-semibold tracking-[-0.02em] text-text-primary">
            最近创作
          </h2>
          <span
            className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium"
            style={{
              background: "var(--bg-muted)",
              color: "var(--text-tertiary)",
            }}
          >
            {projects.length} 个
          </span>
        </div>
        <Link
          href="/workspace/lobby"
          className="inline-flex items-center gap-1 text-[13px] font-medium transition-colors duration-200 hover:text-text-primary"
          style={{ color: "var(--text-tertiary)" }}
        >
          查看全部
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
        </Link>
      </div>

      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide"
        style={{ scrollSnapType: "x mandatory" }}
      >
        {projects.map((project, index) => {
          const isHovered = hoveredId === project.id;
          const tone = resolveProjectCardTone(project.id);

          return (
            <Link
              key={project.id}
              href={`/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}
              className="group relative flex-shrink-0 overflow-hidden rounded-2xl transition-all duration-400"
              onMouseEnter={() => setHoveredId(project.id)}
              onMouseLeave={() => setHoveredId(null)}
              style={{
                minWidth: "160px",
                width: isHovered ? "min(280px, 90vw)" : "min(180px, 70vw)",
                maxWidth: "280px",
                scrollSnapAlign: "start",
                background: "var(--bg-surface)",
                border: `1px solid ${isHovered ? "var(--line-medium)" : "transparent"}`,
                boxShadow: isHovered ? "var(--shadow-lg)" : "var(--shadow-xs)",
                opacity: mounted ? 1 : 0,
                transform: mounted ? "translateX(0)" : "translateX(20px)",
                transition: `all 0.5s cubic-bezier(0.4, 0, 0.2, 1) ${0.5 + index * 0.08}s, width 0.4s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease`,
              }}
            >
              {/* 顶部色条 */}
              <div
                className="h-1 transition-all duration-300"
                style={{
                  background: tone.accent,
                  opacity: isHovered ? 0.9 : 0.5,
                }}
              />

              <div className="p-4">
                {/* 首字母 + 标题 */}
                <div className="flex items-start gap-3">
                  <span
                    className="flex w-10 h-10 shrink-0 items-center justify-center rounded-xl font-serif text-[1.1rem] font-semibold transition-all duration-300"
                    style={{
                      background: `${tone.accent}18`,
                      color: tone.accent,
                      transform: isHovered ? "scale(1.05)" : "scale(1)",
                    }}
                  >
                    {project.name.charAt(0)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-serif text-[15px] font-semibold tracking-[-0.02em] truncate text-text-primary">
                      {project.name}
                    </h3>
                    <p className="mt-0.5 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
                      {project.genre ?? "未定题材"}
                    </p>
                  </div>
                </div>

                {/* 悬停展开的详情 */}
                <div
                  className="overflow-hidden transition-all duration-400"
                  style={{
                    maxHeight: isHovered ? "80px" : "0px",
                    opacity: isHovered ? 1 : 0,
                    marginTop: isHovered ? "12px" : "0px",
                  }}
                >
                  <div className="flex items-center gap-2 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium"
                      style={{
                        background: project.status === "active" ? "var(--accent-success-soft)" : "var(--bg-muted)",
                        color: project.status === "active" ? "var(--accent-success)" : "var(--text-tertiary)",
                      }}
                    >
                      {project.status === "active" ? "进行中" : "已完成"}
                    </span>
                    <span>{project.target_words ? `${(project.target_words / 10000).toFixed(1)}万字` : "未设定"}</span>
                  </div>
                  <p className="mt-2 text-[12px] leading-relaxed line-clamp-2" style={{ color: "var(--text-tertiary)" }}>
                    上次更新于 {formatTimeAgo(project.updated_at)}
                  </p>
                </div>

                {/* 底部进度条 */}
                <div className="mt-3 flex items-center gap-2">
                  <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-muted)" }}>
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, (project.current_words ?? 0) / (project.target_words ?? 1) * 100)}%`,
                        background: tone.accent,
                        opacity: 0.7,
                      }}
                    />
                  </div>
                  <span className="text-[11px] whitespace-nowrap" style={{ color: "var(--text-tertiary)" }}>
                    {Math.round((project.current_words ?? 0) / (project.target_words ?? 1) * 100)}%
                  </span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

/* ============================================================
   DashboardAtmosphere — 背景氛围层
   ============================================================ */

function DashboardAtmosphere({ mounted }: Readonly<{ mounted: boolean }>) {
  const canvasRef = useParticleCanvas({
    maxParticles: 25,
    spawnChance: 0.03,
    speed: 0.08,
    minLife: 500,
    maxLife: 600,
    minSize: 0.2,
    maxSize: 0.8,
    alpha: 0.12,
    fadeInFrames: 100,
    fadeOutFrames: 150,
  });

  return (
    <>
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ opacity: mounted ? 1 : 0, transition: "opacity 2s ease" }}
      />
      <div
        className="absolute top-0 right-0 w-[500px] h-[400px] rounded-full blur-3xl pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(160,150,130,0.05) 0%, transparent 70%)",
          opacity: mounted ? 1 : 0,
          transition: "opacity 2s ease 0.5s",
        }}
      />
      <div
        className="absolute bottom-[10%] left-0 w-[400px] h-[300px] rounded-full blur-3xl pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(110,140,170,0.04) 0%, transparent 70%)",
          opacity: mounted ? 1 : 0,
          transition: "opacity 2s ease 0.8s",
        }}
      />
    </>
  );
}

/* ============================================================
   Hooks & Utilities
   ============================================================ */

function useGreeting() {
  return useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 6) return { text: "夜深了", timeLabel: "凌晨时分" };
    if (hour < 9) return { text: "早安", timeLabel: "清晨" };
    if (hour < 12) return { text: "上午好", timeLabel: "上午" };
    if (hour < 14) return { text: "午安", timeLabel: "正午" };
    if (hour < 18) return { text: "下午好", timeLabel: "午后" };
    if (hour < 22) return { text: "晚上好", timeLabel: "夜晚" };
    return { text: "夜深了", timeLabel: "深夜" };
  }, []);
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "刚刚";
  if (diffMins < 60) return `${diffMins} 分钟前`;
  if (diffHours < 24) return `${diffHours} 小时前`;
  if (diffDays < 7) return `${diffDays} 天前`;
  return `${Math.floor(diffDays / 7)} 周前`;
}
