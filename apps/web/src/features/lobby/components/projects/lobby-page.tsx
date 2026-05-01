"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { LobbyProjectShelf } from "@/features/lobby/components/projects/lobby-project-shelf";
import { useLobbyProjectModel } from "@/features/lobby/components/projects/lobby-project-model";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";
import { BinIcon, GearIcon } from "@/components/icons/shared-icons";

export function LobbyPage() {
  const model = useLobbyProjectModel({ deletedOnly: false });
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const lastProjectId = useWorkspaceStore((state) => state.lastProjectId);
  const [mounted, setMounted] = useState(false);

  const handleCreateProject = useCallback(async () => {
    try {
      const detail = await model.createProjectMutation.mutateAsync({
        name: "新作品",
      });
      if (detail?.id) {
        router.push(
          `/workspace/project/${detail.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`,
        );
      }
    } catch {
      // error notice handled by mutation
    }
  }, [model.createProjectMutation, router]);

  useEffect(() => {
    queueMicrotask(() => setMounted(true));
  }, []);

  return (
    <div
      className="relative workspace-shell--lobby"
    >
      {/* === 背景层：微光渐变 === */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(circle at top left, rgba(160,150,130,0.04), transparent 32%), radial-gradient(circle at right 20%, rgba(110,140,170,0.035), transparent 26%)",
          opacity: mounted ? 1 : 0,
          transition: "opacity 2s ease",
        }}
      />

      {/* === 顶部导航 === */}
      <nav
        className="relative z-30 flex-none flex items-center justify-between px-6 py-4 lg:px-10"
        style={{
          opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(-16px)",
          transition: "all 1.2s cubic-bezier(0.4, 0, 0.2, 1) 0.4s",
        }}
      >
        <Link href="/" className="flex items-center gap-3 group">
          <span
            className="inline-flex items-center justify-center w-9 h-9 rounded-xl text-[12px] font-bold tracking-[0.15em]"
            style={{
              background:
                "linear-gradient(135deg, var(--accent-primary), var(--accent-primary-dark))",
              color: "var(--text-on-accent)",
            }}
          >
            ES
          </span>
          <span
            className="text-[15px] font-medium tracking-[-0.01em]"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-serif)",
            }}
          >
            easyStory
          </span>
        </Link>

        <div className="flex items-center gap-4">
          {/* 搜索 */}
          <div
            className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--line-soft)",
              boxShadow: "var(--shadow-xs)",
            }}
          >
            <svg
              className="w-3.5 h-3.5"
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
              className="bg-transparent text-[13px] outline-none w-[120px]"
              style={{
                color: "var(--text-secondary)",
                caretColor: "var(--accent-primary)",
              }}
              placeholder="寻书..."
              value={model.searchText}
              onChange={(e) => model.setSearchText(e.target.value)}
            />
          </div>

          {/* 用户名 */}
          <span
            className="hidden md:block text-[13px]"
            style={{ color: "var(--text-tertiary)" }}
          >
            {user?.username ?? "未登录"}
          </span>

          {/* 退出 */}
          <button
            onClick={clearSession}
            className="ink-link-button text-[12px] tracking-[0.05em]"
          >
            退出
          </button>
        </div>
      </nav>

      {/* === 可滚动内容区 === */}
      <div
        className="relative z-20 flex-1 overflow-y-auto overflow-x-hidden"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: "var(--line-medium) transparent",
        }}
      >
        <main className="px-6 lg:px-10 pb-32">
          {/* 书阁标题 */}
          <header
            className="mb-10 mt-2"
            style={{
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(20px)",
              transition: "all 1.4s cubic-bezier(0.4, 0, 0.2, 1) 0.6s",
            }}
          >
            <div className="flex items-end gap-6">
              <div>
                <h1
                  className="text-[clamp(2rem,5vw,3.5rem)] font-semibold leading-none tracking-[-0.04em]"
                  style={{
                    color: "var(--text-primary)",
                    fontFamily: "var(--font-serif)",
                  }}
                >
                  墨海书阁
                </h1>
                <p
                  className="mt-3 text-[14px] tracking-[0.1em]"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {model.projectsQuery.data?.length ?? 0} 卷藏书
                </p>
              </div>
              <div
                className="hidden md:block flex-1 h-px mb-3"
                style={{
                  background:
                    "linear-gradient(90deg, var(--line-medium), transparent)",
                }}
              />
            </div>
          </header>

          {/* 项目展示 */}
          <div
            style={{
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(24px)",
              transition: "all 1.2s cubic-bezier(0.4, 0, 0.2, 1) 0.9s",
            }}
          >
            <LobbyProjectShelf
              actionMutation={model.actionMutation}
              deletedOnly={false}
              error={model.projectsQuery.error}
              isLoading={model.projectsQuery.isLoading}
              projects={model.filteredProjects}
              viewMode="grid"
            />
          </div>
        </main>
      </div>

      {/* === 底部工具栏 === */}
      <footer
        className="fixed bottom-6 left-0 right-0 z-30 flex justify-center pointer-events-none"
        style={{
          opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)",
          transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 1.2s",
        }}
      >
        <div className="pointer-events-auto lobby-toolbar">
          <ToolButton
            icon={<WorkflowToolbarIcon />}
            label="工作流"
            href={lastProjectId ? `/workspace/project/${lastProjectId}/engine` : ""}
            disabled={!lastProjectId}
          />
          <ToolButton
            icon={<AnalysisToolbarIcon />}
            label="分析"
            href={lastProjectId ? `/workspace/project/${lastProjectId}/lab` : ""}
            disabled={!lastProjectId}
          />
          <NewProjectButton
            isPending={model.createProjectMutation.isPending}
            onClick={handleCreateProject}
          />
          <ToolButton
            icon={<BinIcon />}
            label="回收"
            href="/workspace/lobby/recycle-bin"
          />
          <ToolButton
            icon={<GearIcon />}
            label="设置"
            href="/workspace/lobby/settings"
          />
        </div>
      </footer>
    </div>
  );
}

/* ============================================================
   底部工具按钮
   ============================================================ */

function NewProjectButton({
  isPending,
  onClick,
}: {
  isPending: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className="lobby-toolbar-btn lobby-toolbar-btn--new"
      disabled={isPending}
      onClick={onClick}
      type="button"
    >
      <svg
        className="lobby-toolbar-btn__icon"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--text-on-accent)"
        strokeWidth="2.5"
        strokeLinecap="round"
      >
        <path d="M12 5v14M5 12h14" />
      </svg>
      <span className="lobby-toolbar-btn__label">
        {isPending ? "创建中..." : "新建"}
      </span>
    </button>
  );
}

function ToolButton({
  icon,
  label,
  href,
  tone,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  href: string;
  tone?: "primary" | "default";
  disabled?: boolean;
}) {
  const isPrimary = tone === "primary";

  if (disabled) {
    return (
      <span
        className="lobby-toolbar-btn lobby-toolbar-btn--disabled"
        title="最近没有打开过项目"
      >
        <span className="lobby-toolbar-btn__icon">{icon}</span>
        <span className="lobby-toolbar-btn__label">{label}</span>
      </span>
    );
  }

  return (
    <Link
      href={href}
      className={`lobby-toolbar-btn ${isPrimary ? "lobby-toolbar-btn--primary" : ""}`}
    >
      <span className="lobby-toolbar-btn__icon">{icon}</span>
      <span className="lobby-toolbar-btn__label">{label}</span>
    </Link>
  );
}

function WorkflowToolbarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
      <path d="m5.64 5.64 2.83 2.83M15.54 8.47l2.83-2.83M5.64 18.36l2.83-2.83M15.54 15.54l2.83 2.83" />
    </svg>
  );
}

function AnalysisToolbarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="m7 16 4-8 4 4 4-6" />
    </svg>
  );
}
