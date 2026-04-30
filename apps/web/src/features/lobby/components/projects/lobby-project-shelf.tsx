"use client";

import { useState, type CSSProperties } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";

import { StatusBadge } from "@/components/ui/status-badge";
import type { ProjectActionVariables } from "@/features/lobby/components/projects/lobby-project-model";
import {
  formatProjectTargetWords,
  formatProjectTrashDeadline,
  formatProjectTrashTime,
  formatProjectUpdatedTime,
  resolveProjectCardTone,
} from "@/features/lobby/components/projects/lobby-project-support";
import { ProjectDeleteConfirmDialog, RecycleBinDeleteDialog } from "@/features/lobby/components/recycle-bin/recycle-bin-dialogs";
import { getErrorMessage } from "@/lib/api/client";
import type { ProjectDetail, ProjectSummary } from "@/lib/api/types";

type ProjectActionMutation = UseMutationResult<ProjectDetail | void, unknown, ProjectActionVariables>;

type LobbyProjectShelfProps = {
  actionMutation: ProjectActionMutation;
  deletedOnly: boolean;
  error: unknown;
  isLoading: boolean;
  projects: ProjectSummary[];
  templateNameById: Map<string, string>;
  viewMode?: "grid" | "list";
};

export function LobbyProjectShelf({
  actionMutation,
  deletedOnly,
  error,
  isLoading,
  projects,
  templateNameById,
  viewMode = "grid",
}: Readonly<LobbyProjectShelfProps>) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div
          className="w-8 h-8 border-2 rounded-full animate-spin"
          style={{
            borderColor: "var(--line-soft)",
            borderTopColor: "var(--accent-primary)",
          }}
        />
        <p className="text-[0.9rem] text-text-secondary">
          正在加载作品列表…
        </p>
      </div>
    );
  }
  if (error) {
    return (
      <div
        className="px-4 py-4 rounded-2xl text-[0.92rem] bg-accent-danger-soft text-accent-danger"
      >
        {getErrorMessage(error)}
      </div>
    );
  }
  if (projects.length === 0) {
    return <ProjectShelfEmptyState deletedOnly={deletedOnly} />;
  }

  if (viewMode === "list") {
    return (
      <div className="flex flex-col gap-2">
        {projects.map((project) => (
          <LobbyProjectListItem
            actionMutation={actionMutation}
            key={project.id}
            project={project}
            templateName={project.template_id ? templateNameById.get(project.template_id) ?? "已绑定模板" : "无"}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:gap-5 [grid-template-columns:repeat(auto-fill,minmax(min(100%,280px),1fr))]">
      {projects.map((project) => (
        <LobbyProjectCard
          actionMutation={actionMutation}
          key={project.id}
          project={project}
          templateName={project.template_id ? templateNameById.get(project.template_id) ?? "已绑定模板" : "无"}
        />
      ))}
    </div>
  );
}

function ProjectShelfEmptyState({ deletedOnly }: Readonly<{ deletedOnly: boolean }>) {
  return (
    <div
      className="flex flex-col items-center justify-center py-24 px-6 rounded-3xl text-center bg-surface"
    >
      <div
        className="flex w-16 h-16 items-center justify-center mb-5 rounded-2xl bg-accent-primary-soft text-accent-primary"
      >
        <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
      </div>
      <h3
        className="m-0 mb-2 font-serif text-[1.25rem] font-semibold tracking-[-0.03em] text-text-primary"
      >
        {deletedOnly ? "回收站为空" : "还没有作品"}
      </h3>
      <p
        className="max-w-[24rem] m-0 text-[0.9rem] leading-relaxed text-text-secondary"
      >
        {deletedOnly
          ? "当前没有已删除项目。删除后的项目会保留在回收站里，随时可以恢复。"
          : "新建作品后，它会作为一张书卡出现在这里，直接回到创作现场。"}
      </p>
      {!deletedOnly && (
        <Link className="ink-button mt-6" href="/workspace/lobby/new">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          新建作品
        </Link>
      )}
    </div>
  );
}

function LobbyProjectListItem({
  actionMutation,
  project,
  templateName,
}: Readonly<{
  actionMutation: ProjectActionMutation;
  project: ProjectSummary;
  templateName: string;
}>) {
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isSoftDeleteDialogOpen, setSoftDeleteDialogOpen] = useState(false);
  const isDeleted = Boolean(project.deleted_at);
  const isPhysicalDeleting = isPendingProjectAction(actionMutation, project.id, "physicalDelete");
  const isSoftDeleting = isPendingProjectAction(actionMutation, project.id, "delete");
  const physicalDeleteErrorMessage = resolveProjectActionErrorMessage(actionMutation, project.id, "physicalDelete");
  const softDeleteErrorMessage = resolveProjectActionErrorMessage(actionMutation, project.id, "delete");
  const tone = resolveProjectCardTone(project.id);

  const handleOpenPhysicalDeleteDialog = () => {
    resetProjectActionError(actionMutation, project.id, "physicalDelete");
    setDeleteDialogOpen(true);
  };

  const handleOpenSoftDeleteDialog = () => {
    resetProjectActionError(actionMutation, project.id, "delete");
    setSoftDeleteDialogOpen(true);
  };

  const handleConfirmPhysicalDelete = async () => {
    try {
      await actionMutation.mutateAsync({ projectId: project.id, type: "physicalDelete" });
      setDeleteDialogOpen(false);
    } catch {
      // Keep the dialog open so the user can see the inline error and retry.
    }
  };

  const handleConfirmSoftDelete = async () => {
    try {
      await actionMutation.mutateAsync({ projectId: project.id, type: "delete" });
      setSoftDeleteDialogOpen(false);
    } catch {
      // Keep the dialog open so the user can see the inline error and retry.
    }
  };

  return (
    <article
      className={`group flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all ${isDeleted ? "opacity-60" : ""}`}
      style={
        {
          background: "var(--bg-surface)",
          boxShadow: "var(--shadow-xs)",
          "--project-card-accent": tone.accent,
        } as CSSProperties
      }
    >
      {/* 颜色指示条 */}
      <div
        className="w-1 h-10 rounded-full shrink-0"
        style={{ background: tone.accent }}
      />

      {/* 首字母头像 */}
      <span
        className="flex w-9 h-9 shrink-0 items-center justify-center rounded-xl font-serif text-[1rem] font-semibold"
        style={{ background: `${tone.accent}18`, color: tone.accent }}
      >
        {project.name.charAt(0)}
      </span>

      {/* 信息 */}
      <div className="flex-1 min-w-0 grid gap-0.5">
        <div className="flex items-center gap-2 min-w-0">
          <h3
            className="m-0 min-w-0 text-[0.95rem] font-semibold tracking-[-0.02em] truncate text-text-primary"
          >
            {project.name}
          </h3>
          <StatusBadge status={project.status} />
          {isDeleted && <StatusBadge label="回收站" status="archived" />}
        </div>
        <div
          className="flex items-center gap-3 text-[0.76rem] text-text-tertiary"
        >
          <span>{project.genre ?? "未定题材"}</span>
          <span className="w-px h-3" style={{ background: "var(--line-soft)" }} />
          <span>{formatProjectTargetWords(project.target_words)}</span>
          <span className="w-px h-3" style={{ background: "var(--line-soft)" }} />
          <span>{templateName === "无" ? "自由创作" : templateName}</span>
        </div>
      </div>

      {/* 时间 */}
      <span
        className="hidden md:block text-[0.76rem] whitespace-nowrap [font-variant-numeric:tabular-nums] text-text-tertiary"
      >
        {isDeleted
          ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
          : `更新于 ${formatProjectUpdatedTime(project.updated_at)}`}
      </span>

      {/* 操作 */}
      <div className="flex items-center gap-1.5 shrink-0">
        {isDeleted ? (
          <>
            <button
              className="ink-button text-[0.8rem] h-8 px-3"
              disabled={actionMutation.isPending}
              onClick={() => actionMutation.mutate({ projectId: project.id, type: "restore" })}
              type="button"
            >
              恢复
            </button>
            <button
              className="ink-button-danger text-[0.8rem] h-8 px-3"
              disabled={actionMutation.isPending}
              onClick={handleOpenPhysicalDeleteDialog}
              type="button"
            >
              删除
            </button>
          </>
        ) : (
          <>
            <Link
              className="ink-button text-[0.8rem] h-8 px-3"
              href={`/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}
            >
              继续
            </Link>
            <Link
              className="ink-icon-button"
              href={`/workspace/project/${project.id}/settings`}
              title="项目设置"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </Link>
            <button
              className="ink-icon-button"
              disabled={actionMutation.isPending}
              onClick={handleOpenSoftDeleteDialog}
              type="button"
              title="移入回收站"
              style={{ color: "var(--accent-danger)" }}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          </>
        )}
      </div>

      {isDeleteDialogOpen ? (
        <RecycleBinDeleteDialog
          errorMessage={physicalDeleteErrorMessage}
          isPending={isPhysicalDeleting}
          onClose={() => setDeleteDialogOpen(false)}
          onConfirm={handleConfirmPhysicalDelete}
          project={project}
        />
      ) : null}
      {isSoftDeleteDialogOpen ? (
        <ProjectDeleteConfirmDialog
          errorMessage={softDeleteErrorMessage}
          isPending={isSoftDeleting}
          onClose={() => setSoftDeleteDialogOpen(false)}
          onConfirm={handleConfirmSoftDelete}
          project={project}
        />
      ) : null}
    </article>
  );
}

function LobbyProjectCard({
  actionMutation,
  project,
  templateName,
}: Readonly<{
  actionMutation: ProjectActionMutation;
  project: ProjectSummary;
  templateName: string;
}>) {
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isSoftDeleteDialogOpen, setSoftDeleteDialogOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const isDeleted = Boolean(project.deleted_at);
  const isPhysicalDeleting = isPendingProjectAction(actionMutation, project.id, "physicalDelete");
  const isSoftDeleting = isPendingProjectAction(actionMutation, project.id, "delete");
  const physicalDeleteErrorMessage = resolveProjectActionErrorMessage(
    actionMutation,
    project.id,
    "physicalDelete",
  );
  const softDeleteErrorMessage = resolveProjectActionErrorMessage(
    actionMutation,
    project.id,
    "delete",
  );
  const tone = resolveProjectCardTone(project.id);

  const handleOpenPhysicalDeleteDialog = () => {
    resetProjectActionError(actionMutation, project.id, "physicalDelete");
    setDeleteDialogOpen(true);
  };

  const handleOpenSoftDeleteDialog = () => {
    resetProjectActionError(actionMutation, project.id, "delete");
    setSoftDeleteDialogOpen(true);
  };

  const handleConfirmPhysicalDelete = async () => {
    try {
      await actionMutation.mutateAsync({ projectId: project.id, type: "physicalDelete" });
      setDeleteDialogOpen(false);
    } catch {
      // Keep the dialog open so the user can see the inline error and retry.
    }
  };

  const handleConfirmSoftDelete = async () => {
    try {
      await actionMutation.mutateAsync({ projectId: project.id, type: "delete" });
      setSoftDeleteDialogOpen(false);
    } catch {
      // Keep the dialog open so the user can see the inline error and retry.
    }
  };

  return (
    <article
      className={`group relative flex min-w-0 flex-col overflow-hidden rounded-2xl transition-all duration-500 ${isDeleted ? "opacity-60" : ""}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={
        {
          background: "linear-gradient(180deg, rgba(45,50,61,0.6) 0%, rgba(36,40,48,0.4) 100%)",
          boxShadow: isHovered
            ? "0 20px 40px rgba(15, 17, 21, 0.4), 0 0 0 1px rgba(201, 169, 110, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08)"
            : "0 4px 12px rgba(15, 17, 21, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.04)",
          border: `1px solid ${isHovered ? "rgba(201, 169, 110, 0.12)" : "rgba(201, 169, 110, 0.04)"}`,
          transform: isHovered ? "translateY(-4px)" : "translateY(0)",
          "--project-card-accent": tone.accent,
          "--project-card-surface": tone.surface,
        } as CSSProperties
      }
    >
      {/* 顶部渐变条 */}
      <div
        className="h-[3px] shrink-0 transition-all duration-500"
        style={{
          background: `linear-gradient(90deg, ${tone.accent} 0%, ${tone.accent}80 50%, transparent 100%)`,
          opacity: isHovered ? 1 : 0.6,
          width: isHovered ? "100%" : "60%",
        }}
      />

      {/* 背景装饰圆 */}
      <div
        className="absolute -top-8 -right-8 w-24 h-24 rounded-full blur-2xl pointer-events-none transition-opacity duration-700"
        style={{
          background: `radial-gradient(circle, ${tone.accent}15 0%, transparent 70%)`,
          opacity: isHovered ? 1 : 0,
        }}
      />

      <div className="relative z-10 grid gap-3 p-5 pb-3 flex-1">
        {/* 标题行 */}
        <div className="flex items-center gap-3 min-w-0">
          <span
            className="flex w-10 h-10 shrink-0 items-center justify-center rounded-xl font-serif text-[1.1rem] font-semibold transition-all duration-300"
            style={{
              background: `${tone.accent}20`,
              color: tone.accent,
              boxShadow: isHovered ? `0 0 20px ${tone.accent}25` : "none",
              transform: isHovered ? "scale(1.05)" : "scale(1)",
            }}
          >
            {project.name.charAt(0)}
          </span>
          <div className="min-w-0 flex-1">
            <h3
              className="m-0 min-w-0 font-serif text-[1.1rem] font-semibold tracking-[-0.03em] leading-tight truncate text-text-primary transition-colors duration-300"
              style={{ color: isHovered ? "var(--text-primary)" : "var(--text-primary)" }}
            >
              {project.name}
            </h3>
            <p className="m-0 text-[0.72rem] text-text-tertiary mt-0.5">
              {project.genre ?? "未定题材"}
            </p>
          </div>
          {!project.deleted_at ? (
            <Link
              className="inline-flex w-7 h-7 shrink-0 items-center justify-center rounded-lg transition-all ml-auto opacity-0 group-hover:opacity-100"
              style={{
                background: "var(--bg-muted)",
                color: "var(--text-tertiary)",
              }}
              href={`/workspace/project/${project.id}/settings`}
              title="项目设置"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </Link>
          ) : null}
        </div>

        {/* 标签 */}
        <div className="flex flex-wrap gap-[0.35rem] items-center">
          <StatusBadge status={project.status} />
          {isDeleted ? <StatusBadge label="回收站" status="archived" /> : null}
          <span
            className="inline-flex items-center h-[1.3rem] px-[0.5rem] rounded-full text-[0.7rem] font-medium"
            style={{
              background: `${tone.accent}12`,
              color: tone.accent,
            }}
          >
            {formatProjectTargetWords(project.target_words)}
          </span>
        </div>

        {/* 描述 */}
        <p
          className="m-0 text-[0.82rem] leading-relaxed line-clamp-2"
          style={{ color: "var(--text-secondary)" }}
        >
          {isDeleted
            ? `项目已移入回收站，保留到 ${formatProjectTrashDeadline(project.deleted_at)}。`
            : `以 ${templateName === "无" ? "自由创作" : templateName} 为起点，继续整理设定、章节和正文。`}
        </p>

        {/* 进度条 */}
        {!isDeleted && (
          <div className="mt-1">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[0.7rem]" style={{ color: "var(--text-tertiary)" }}>
                创作进度
              </span>
              <span className="text-[0.7rem] font-medium" style={{ color: tone.accent }}>
                {Math.round((project.current_words ?? 0) / (project.target_words ?? 1) * 100)}%
              </span>
            </div>
            <div className="h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-muted)" }}>
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${Math.min(100, (project.current_words ?? 0) / (project.target_words ?? 1) * 100)}%`,
                  background: `linear-gradient(90deg, ${tone.accent}90, ${tone.accent})`,
                  boxShadow: isHovered ? `0 0 8px ${tone.accent}40` : "none",
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 底部操作栏 */}
      <div
        className="relative z-10 flex items-center justify-between gap-3 px-5 pb-4 pt-3 mt-auto"
        style={{
          background: "linear-gradient(180deg, transparent 0%, rgba(36,40,48,0.5) 100%)",
          borderTop: "1px solid rgba(201, 169, 110, 0.04)",
        }}
      >
        <span
          className="text-[0.72rem] leading-relaxed [font-variant-numeric:tabular-nums]"
          style={{ color: "var(--text-tertiary)" }}
        >
          {isDeleted
            ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
            : `更新于 ${formatProjectUpdatedTime(project.updated_at)}`}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {isDeleted ? (
            <>
              <button
                className="ink-button text-[0.75rem] h-7 px-2.5"
                disabled={actionMutation.isPending}
                onClick={() => actionMutation.mutate({ projectId: project.id, type: "restore" })}
                type="button"
              >
                恢复
              </button>
              <button
                className="ink-button-danger text-[0.75rem] h-7 px-2.5"
                disabled={actionMutation.isPending}
                onClick={handleOpenPhysicalDeleteDialog}
                type="button"
              >
                彻底删除
              </button>
            </>
          ) : (
            <>
              <Link
                className="inline-flex items-center justify-center gap-1.5 h-8 px-4 rounded-full text-[0.8rem] font-semibold transition-all duration-300"
                style={{
                  background: isHovered ? tone.accent : `${tone.accent}15`,
                  color: isHovered ? "var(--text-on-accent)" : tone.accent,
                  boxShadow: isHovered ? `0 4px 16px ${tone.accent}30` : "none",
                }}
                href={`/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
                继续
              </Link>
              <button
                className="inline-flex items-center justify-center w-8 h-8 rounded-full transition-all duration-300"
                disabled={actionMutation.isPending}
                onClick={handleOpenSoftDeleteDialog}
                type="button"
                title="移入回收站"
                style={{
                  background: isHovered ? "var(--accent-danger-soft)" : "transparent",
                  color: "var(--accent-danger)",
                }}
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </>
          )}
        </div>
      </div>

      {isDeleteDialogOpen ? (
        <RecycleBinDeleteDialog
          errorMessage={physicalDeleteErrorMessage}
          isPending={isPhysicalDeleting}
          onClose={() => setDeleteDialogOpen(false)}
          onConfirm={handleConfirmPhysicalDelete}
          project={project}
        />
      ) : null}
      {isSoftDeleteDialogOpen ? (
        <ProjectDeleteConfirmDialog
          errorMessage={softDeleteErrorMessage}
          isPending={isSoftDeleting}
          onClose={() => setSoftDeleteDialogOpen(false)}
          onConfirm={handleConfirmSoftDelete}
          project={project}
        />
      ) : null}
    </article>
  );
}

function isPendingProjectAction(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  return actionMutation.isPending && matchesProjectAction(actionMutation, projectId, type);
}

function resolveProjectActionErrorMessage(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  if (!actionMutation.isError || !matchesProjectAction(actionMutation, projectId, type)) {
    return null;
  }
  return getErrorMessage(actionMutation.error);
}

function resetProjectActionError(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  if (!actionMutation.isError || !matchesProjectAction(actionMutation, projectId, type)) {
    return;
  }
  actionMutation.reset();
}

function matchesProjectAction(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  return (
    actionMutation.variables?.projectId === projectId &&
    actionMutation.variables?.type === type
  );
}
