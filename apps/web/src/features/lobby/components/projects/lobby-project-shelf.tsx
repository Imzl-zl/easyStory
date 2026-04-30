"use client";

import { useState } from "react";
import type { CSSProperties } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";

import type { ProjectActionVariables } from "@/features/lobby/components/projects/lobby-project-model";
import {
  formatProjectTargetWords,
  formatProjectTrashDeadline,
  formatProjectTrashTime,
  formatProjectUpdatedTime,
  resolveProjectCardTone,
} from "@/features/lobby/components/projects/lobby-project-support";
import {
  ProjectDeleteConfirmDialog,
  RecycleBinDeleteDialog,
} from "@/features/lobby/components/recycle-bin/recycle-bin-dialogs";
import { getErrorMessage } from "@/lib/api/client";
import type { ProjectDetail, ProjectSummary } from "@/lib/api/types";

type ProjectActionMutation = UseMutationResult<
  ProjectDetail | void,
  unknown,
  ProjectActionVariables
>;

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
    return <ProjectShelfLoadingState />;
  }

  if (error) {
    return <ProjectShelfErrorState error={error} />;
  }

  if (projects.length === 0) {
    return <ProjectShelfEmptyState deletedOnly={deletedOnly} />;
  }

  if (viewMode === "list") {
    return (
      <div className="flex flex-col gap-3">
        {projects.map((project) => (
          <LobbyProjectListItem
            actionMutation={actionMutation}
            key={project.id}
            project={project}
            templateName={
              project.template_id
                ? (templateNameById.get(project.template_id) ?? "已绑定模板")
                : "无"
            }
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-5 sm:gap-6 [grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr))]">
      {projects.map((project, index) => (
        <LobbyProjectCard
          actionMutation={actionMutation}
          key={project.id}
          project={project}
          templateName={
            project.template_id
              ? (templateNameById.get(project.template_id) ?? "已绑定模板")
              : "无"
          }
          index={index}
        />
      ))}
    </div>
  );
}

/* ============================================================
   加载状态
   ============================================================ */

function ProjectShelfLoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-5">
      <div className="relative w-10 h-10">
        <div
          className="absolute inset-0 rounded-full animate-spin"
          style={{
            border: "1.5px solid transparent",
            borderTopColor: "var(--accent-primary)",
            borderRightColor: "var(--line-soft)",
          }}
        />
      </div>
      <p
        className="text-[14px] tracking-[0.1em]"
        style={{ color: "var(--text-tertiary)" }}
      >
        整理书卷中...
      </p>
    </div>
  );
}

/* ============================================================
   错误状态
   ============================================================ */

function ProjectShelfErrorState({ error }: { error: unknown }) {
  return (
    <div
      className="px-6 py-5 rounded-2xl text-[14px]"
      style={{
        background: "var(--callout-danger-bg)",
        color: "var(--accent-danger)",
        border: "1px solid var(--callout-danger-border)",
      }}
    >
      {getErrorMessage(error)}
    </div>
  );
}

/* ============================================================
   空状态
   ============================================================ */

function ProjectShelfEmptyState({
  deletedOnly,
}: Readonly<{ deletedOnly: boolean }>) {
  return (
    <div className="flex flex-col items-center justify-center py-32 px-6 text-center">
      <div
        className="relative w-20 h-20 mb-8 flex items-center justify-center rounded-full"
        style={{
          background:
            "radial-gradient(circle, var(--accent-primary-soft) 0%, transparent 70%)",
        }}
      >
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--text-tertiary)"
          strokeWidth="1"
          strokeLinecap="round"
        >
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
      </div>
      <h3
        className="text-[18px] font-medium tracking-[0.05em] mb-2"
        style={{
          color: "var(--text-secondary)",
          fontFamily: "var(--font-serif)",
        }}
      >
        {deletedOnly ? "回收站为空" : "书阁尚空"}
      </h3>
      <p
        className="max-w-[22rem] text-[13px] leading-relaxed"
        style={{ color: "var(--text-tertiary)" }}
      >
        {deletedOnly
          ? "当前没有已删除项目。删除后的项目会保留在回收站里，随时可以恢复。"
          : "提笔写下第一卷，或从模板中择一而始。"}
      </p>
      {!deletedOnly && (
        <Link
          href="/workspace/lobby/new"
          className="ink-button mt-8"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
          开卷提笔
        </Link>
      )}
    </div>
  );
}

/* ============================================================
   书卷卡片
   ============================================================ */

function LobbyProjectCard({
  actionMutation,
  project,
  templateName,
  index,
}: Readonly<{
  actionMutation: ProjectActionMutation;
  project: ProjectSummary;
  templateName: string;
  index: number;
}>) {
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isSoftDeleteDialogOpen, setSoftDeleteDialogOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const isDeleted = Boolean(project.deleted_at);
  const isPhysicalDeleting = isPendingProjectAction(
    actionMutation,
    project.id,
    "physicalDelete",
  );
  const isSoftDeleting = isPendingProjectAction(
    actionMutation,
    project.id,
    "delete",
  );
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
      await actionMutation.mutateAsync({
        projectId: project.id,
        type: "physicalDelete",
      });
      setDeleteDialogOpen(false);
    } catch {
      // Keep dialog open for retry
    }
  };

  const handleConfirmSoftDelete = async () => {
    try {
      await actionMutation.mutateAsync({
        projectId: project.id,
        type: "delete",
      });
      setSoftDeleteDialogOpen(false);
    } catch {
      // Keep dialog open for retry
    }
  };

  const progress = Math.min(
    100,
    ((project.current_words ?? 0) / (project.target_words ?? 1)) * 100,
  );

  return (
    <article
      className={`group relative flex flex-col overflow-hidden transition-all duration-700 ${isDeleted ? "opacity-50" : ""}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: isHovered
          ? "var(--bg-surface)"
          : "var(--bg-glass)",
        borderRadius: "var(--radius-2xl)",
        border: `1px solid ${isHovered ? "var(--line-medium)" : "var(--line-soft)"}`,
        boxShadow: isHovered
          ? "var(--shadow-lg)"
          : "var(--shadow-sm)",
        transform: isHovered
          ? "translateY(-6px) scale(1.01)"
          : "translateY(0) scale(1)",
        transitionDelay: `${index * 60}ms`,
      }}
    >
      {/* 顶部装饰线 */}
      <div
        className="h-[2px] transition-all duration-500"
        style={{
          background: `linear-gradient(90deg, ${tone.accent}90, ${tone.accent}40, transparent)`,
          opacity: isHovered ? 1 : 0.5,
          width: isHovered ? "100%" : "40%",
        }}
      />

      {/* 背景光晕 */}
      <div
        className="absolute -top-10 -right-10 w-32 h-32 rounded-full pointer-events-none transition-opacity duration-700"
        style={{
          background: `radial-gradient(circle, ${tone.accent}12 0%, transparent 70%)`,
          opacity: isHovered ? 1 : 0,
        }}
      />

      <div className="relative z-10 p-6 flex-1 flex flex-col">
        {/* 标题行 */}
        <div className="flex items-start gap-4">
          {/* 书卷首字印章 */}
          <div
            className="relative flex w-12 h-12 shrink-0 items-center justify-center rounded-xl transition-all duration-500"
            style={{
              background: `${tone.accent}15`,
              border: `1px solid ${tone.accent}30`,
              boxShadow: isHovered ? `0 0 24px ${tone.accent}20` : "none",
            }}
          >
            <span
              className="text-[18px] font-bold"
              style={{
                color: tone.accent,
                fontFamily: "var(--font-serif)",
              }}
            >
              {project.name.charAt(0)}
            </span>
          </div>

          <div className="flex-1 min-w-0">
            <h3
              className="text-[16px] font-medium tracking-[-0.01em] truncate transition-colors duration-300"
              style={{
                color: isHovered
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
              }}
            >
              {project.name}
            </h3>
            <p
              className="mt-0.5 text-[12px]"
              style={{ color: "var(--text-tertiary)" }}
            >
              {project.genre ?? "未定题材"}
            </p>
          </div>

          {/* 状态 */}
          <div className="shrink-0">
            <InkStatusBadge status={project.status} />
          </div>
        </div>

        {/* 信息行 */}
        <div
          className="mt-4 flex items-center gap-3 text-[11px]"
          style={{ color: "var(--text-tertiary)" }}
        >
          <span>{formatProjectTargetWords(project.target_words)}</span>
          <span style={{ color: "var(--line-medium)" }}>·</span>
          <span>
            {templateName === "无" ? "自由创作" : templateName}
          </span>
        </div>

        {/* 进度 */}
        {!isDeleted && project.target_words && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span
                className="text-[11px]"
                style={{ color: "var(--text-tertiary)" }}
              >
                创作进度
              </span>
              <span
                className="text-[11px] font-medium tabular-nums"
                style={{ color: tone.accent }}
              >
                {Math.round(progress)}%
              </span>
            </div>
            <div
              className="h-[3px] rounded-full overflow-hidden"
              style={{ background: "var(--line-soft)" }}
            >
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: `${progress}%`,
                  background: `linear-gradient(90deg, ${tone.accent}60, ${tone.accent})`,
                  boxShadow: isHovered
                    ? `0 0 8px ${tone.accent}30`
                    : "none",
                }}
              />
            </div>
          </div>
        )}

        {/* 描述 */}
        <p
          className="mt-4 text-[12px] leading-relaxed line-clamp-2 flex-1"
          style={{ color: "var(--text-tertiary)" }}
        >
          {isDeleted
            ? `已移入回收站，保留至 ${formatProjectTrashDeadline(project.deleted_at)}。`
            : `以 ${templateName === "无" ? "自由创作" : templateName} 为起点，继续整理设定与章节。`}
        </p>

        {/* 底部操作 */}
        <div
          className="mt-5 pt-4 flex items-center justify-between"
          style={{ borderTop: "1px solid var(--line-soft)" }}
        >
          <span
            className="text-[11px] tabular-nums"
            style={{ color: "var(--text-tertiary)" }}
          >
            {isDeleted
              ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
              : `更新于 ${formatProjectUpdatedTime(project.updated_at)}`}
          </span>

          <div className="flex items-center gap-2">
            {isDeleted ? (
              <>
                <button
                  className="px-3 py-1.5 rounded-lg text-[11px] tracking-[0.05em] transition-all duration-200 hover:scale-105"
                  style={{
                    background: "var(--accent-success-soft)",
                    color: "var(--accent-success)",
                    border: "1px solid var(--accent-success-muted)",
                  }}
                  disabled={actionMutation.isPending}
                  onClick={() =>
                    actionMutation.mutate({
                      projectId: project.id,
                      type: "restore",
                    })
                  }
                  type="button"
                >
                  恢复
                </button>
                <button
                  className="px-3 py-1.5 rounded-lg text-[11px] tracking-[0.05em] transition-all duration-200 hover:scale-105"
                  style={{
                    background: "var(--accent-danger-soft)",
                    color: "var(--accent-danger)",
                    border: "1px solid var(--accent-danger-muted)",
                  }}
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
                  href={`/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[12px] font-medium tracking-[0.02em] transition-all duration-300 hover:scale-105"
                  style={{
                    background: isHovered
                      ? `${tone.accent}20`
                      : `${tone.accent}10`,
                    color: tone.accent,
                    border: `1px solid ${isHovered ? `${tone.accent}40` : `${tone.accent}20`}`,
                  }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  >
                    <path d="M5 12h14" />
                    <path d="m12 5 7 7-7 7" />
                  </svg>
                  展卷
                </Link>
                <button
                  className="flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-200 ink-icon-button"
                  disabled={actionMutation.isPending}
                  onClick={handleOpenSoftDeleteDialog}
                  type="button"
                  title="移入回收站"
                >
                  <svg
                    width="13"
                    height="13"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </>
            )}
          </div>
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

/* ============================================================
   状态徽章
   ============================================================ */

function InkStatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    { color: string; bg: string; border: string; label: string }
  > = {
    draft: {
      color: "var(--text-tertiary)",
      bg: "var(--bg-muted)",
      border: "var(--line-soft)",
      label: "草稿",
    },
    active: {
      color: "var(--accent-primary)",
      bg: "var(--accent-primary-soft)",
      border: "var(--accent-primary-muted)",
      label: "进行中",
    },
    completed: {
      color: "var(--accent-success)",
      bg: "var(--accent-success-soft)",
      border: "var(--accent-success-muted)",
      label: "已完成",
    },
    archived: {
      color: "var(--text-tertiary)",
      bg: "var(--bg-muted)",
      border: "var(--line-soft)",
      label: "已归档",
    },
  };

  const c = config[status] ?? config.draft;

  return (
    <span
      className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] tracking-[0.08em] font-medium"
      style={{
        color: c.color,
        background: c.bg,
        border: `1px solid ${c.border}`,
      }}
    >
      {c.label}
    </span>
  );
}

/* ============================================================
   列表视图
   ============================================================ */

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
  const isPhysicalDeleting = isPendingProjectAction(
    actionMutation,
    project.id,
    "physicalDelete",
  );
  const isSoftDeleting = isPendingProjectAction(
    actionMutation,
    project.id,
    "delete",
  );
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
      await actionMutation.mutateAsync({
        projectId: project.id,
        type: "physicalDelete",
      });
      setDeleteDialogOpen(false);
    } catch {
      // Keep dialog open
    }
  };

  const handleConfirmSoftDelete = async () => {
    try {
      await actionMutation.mutateAsync({
        projectId: project.id,
        type: "delete",
      });
      setSoftDeleteDialogOpen(false);
    } catch {
      // Keep dialog open
    }
  };

  return (
    <article
      className={`group flex items-center gap-4 px-5 py-4 rounded-xl transition-all duration-300 ${isDeleted ? "opacity-50" : ""}`}
      style={{
        background: "var(--bg-glass)",
        border: "1px solid var(--line-soft)",
        boxShadow: "var(--shadow-xs)",
        ["--project-card-accent" as string]: tone.accent,
      } as CSSProperties}
    >
      <div
        className="w-[2px] h-8 rounded-full shrink-0"
        style={{ background: tone.accent }}
      />

      <span
        className="flex w-9 h-9 shrink-0 items-center justify-center rounded-lg text-[14px] font-bold"
        style={{
          background: `${tone.accent}12`,
          color: tone.accent,
          fontFamily: "var(--font-serif)",
        }}
      >
        {project.name.charAt(0)}
      </span>

      <div className="flex-1 min-w-0 grid gap-0.5">
        <div className="flex items-center gap-2 min-w-0">
          <h3
            className="min-w-0 text-[14px] font-medium truncate"
            style={{ color: "var(--text-secondary)" }}
          >
            {project.name}
          </h3>
          <InkStatusBadge status={project.status} />
          {isDeleted && <InkStatusBadge status="archived" />}
        </div>
        <div
          className="flex items-center gap-3 text-[11px]"
          style={{ color: "var(--text-tertiary)" }}
        >
          <span>{project.genre ?? "未定题材"}</span>
          <span style={{ color: "var(--line-medium)" }}>·</span>
          <span>{formatProjectTargetWords(project.target_words)}</span>
          <span style={{ color: "var(--line-medium)" }}>·</span>
          <span>
            {templateName === "无" ? "自由创作" : templateName}
          </span>
        </div>
      </div>

      <span
        className="hidden md:block text-[11px] tabular-nums whitespace-nowrap"
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
              className="px-3 py-1.5 rounded-lg text-[11px] transition-all duration-200"
              style={{
                background: "var(--accent-success-soft)",
                color: "var(--accent-success)",
                border: "1px solid var(--accent-success-muted)",
              }}
              disabled={actionMutation.isPending}
              onClick={() =>
                actionMutation.mutate({
                  projectId: project.id,
                  type: "restore",
                })
              }
              type="button"
            >
              恢复
            </button>
            <button
              className="px-3 py-1.5 rounded-lg text-[11px] transition-all duration-200"
              style={{
                background: "var(--accent-danger-soft)",
                color: "var(--accent-danger)",
                border: "1px solid var(--accent-danger-muted)",
              }}
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
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-200"
              style={{
                background: `${tone.accent}12`,
                color: tone.accent,
                border: `1px solid ${tone.accent}25`,
              }}
              href={`/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}
            >
              展卷
            </Link>
            <button
              className="flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-200 ink-icon-button"
              disabled={actionMutation.isPending}
              onClick={handleOpenSoftDeleteDialog}
              type="button"
              title="移入回收站"
            >
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
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

/* ============================================================
   工具函数
   ============================================================ */

function isPendingProjectAction(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  return (
    actionMutation.isPending && matchesProjectAction(actionMutation, projectId, type)
  );
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
