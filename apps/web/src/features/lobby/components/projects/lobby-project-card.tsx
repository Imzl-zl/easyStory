"use client";

import { useState } from "react";
import type { CSSProperties } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

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

/* ============================================================
   Status Badge
   ============================================================ */

export function InkStatusBadge({ status }: { status: string }) {
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
      className="lobby-status-badge"
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
   Project Card
   ============================================================ */

export function LobbyProjectCard({
  actionMutation,
  project,
  index,
}: {
  actionMutation: ProjectActionMutation;
  project: ProjectSummary;
  index: number;
}) {
  const router = useRouter();
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isSoftDeleteDialogOpen, setSoftDeleteDialogOpen] = useState(false);
  const [isEntering, setIsEntering] = useState(false);
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

  const studioHref = `/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`;

  const handleEnterStudio = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    setIsEntering(true);
    setTimeout(() => {
      router.push(studioHref);
    }, 420);
  };

  const cardClasses = [
    "lobby-project-card",
    isDeleted ? "lobby-project-card--deleted" : "",
    isEntering ? "lobby-project-card--entering" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const cardStyle = {
    "--card-accent": tone.accent,
    "--card-accent-glow": `${tone.accent}20`,
    transitionDelay: `${index * 60}ms`,
  } as CSSProperties;

  return (
    <article className={cardClasses} style={cardStyle}>
      {/* Top accent line */}
      <div
        className="lobby-project-card__accent-line"
        style={{
          background: `linear-gradient(90deg, ${tone.accent}90, ${tone.accent}40, transparent)`,
          width: "40%",
        }}
      />

      {/* Background glow */}
      <div
        className="lobby-project-card__glow"
        style={{
          background: `radial-gradient(circle, ${tone.accent}12 0%, transparent 70%)`,
        }}
      />

      <div className="lobby-project-card__body">
        {/* Title row */}
        <div className="lobby-project-card__title-row">
          <div
            className="lobby-project-card__seal"
            style={{
              background: `${tone.accent}15`,
              border: `1px solid ${tone.accent}30`,
            }}
          >
            <span
              className="lobby-project-card__seal-char"
              style={{ color: tone.accent }}
            >
              {project.name.charAt(0)}
            </span>
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="lobby-project-card__title truncate">
              {project.name}
            </h3>
            <p className="lobby-project-card__subtitle">
              {project.genre ?? "未定题材"}
            </p>
          </div>

          <div className="shrink-0">
            <InkStatusBadge status={project.status} />
          </div>
        </div>

        {/* Meta */}
        <div className="lobby-project-card__meta">
          <span>{formatProjectTargetWords(project.target_words)}</span>
        </div>

        {/* Progress */}
        {!isDeleted && project.target_words ? (
          <div className="lobby-project-card__progress">
            <div className="lobby-project-card__progress-header">
              <span className="lobby-project-card__progress-label">
                创作进度
              </span>
              <span
                className="lobby-project-card__progress-value"
                style={{ color: tone.accent }}
              >
                {Math.round(progress)}%
              </span>
            </div>
            <div className="lobby-project-card__progress-track">
              <div
                className="lobby-project-card__progress-fill"
                style={{
                  width: `${progress}%`,
                  background: `linear-gradient(90deg, ${tone.accent}60, ${tone.accent})`,
                }}
              />
            </div>
          </div>
        ) : null}

        {/* Description */}
        <p className="lobby-project-card__desc line-clamp-2">
          {isDeleted
            ? `已移入回收站，保留至 ${formatProjectTrashDeadline(project.deleted_at)}。`
            : "继续整理设定与章节。"}
        </p>

        {/* Footer actions */}
        <div className="lobby-project-card__footer">
          <span className="lobby-project-card__timestamp">
            {isDeleted
              ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
              : `更新于 ${formatProjectUpdatedTime(project.updated_at)}`}
          </span>

          <div className="lobby-project-card__actions">
            {isDeleted ? (
              <>
                <button
                  className="lobby-project-card__restore-btn"
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
                  className="lobby-project-card__delete-btn"
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
                  href={studioHref}
                  onClick={handleEnterStudio}
                  className="lobby-project-card__enter-btn"
                  style={{
                    background: `${tone.accent}10`,
                    color: tone.accent,
                    border: `1px solid ${tone.accent}20`,
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
                <Link
                  className="ink-icon-button"
                  href={`/workspace/project/${project.id}/engine`}
                  title="工作流"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                    <path d="m5.64 5.64 2.83 2.83M15.54 8.47l2.83-2.83M5.64 18.36l2.83-2.83M15.54 15.54l2.83 2.83" />
                  </svg>
                </Link>
                <Link
                  className="ink-icon-button"
                  href={`/workspace/project/${project.id}/lab`}
                  title="分析"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 3v18h18" />
                    <path d="m7 16 4-8 4 4 4-6" />
                  </svg>
                </Link>
                <button
                  className="ink-icon-button"
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
   Utility functions
   ============================================================ */

export function isPendingProjectAction(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  return (
    actionMutation.isPending &&
    matchesProjectAction(actionMutation, projectId, type)
  );
}

export function resolveProjectActionErrorMessage(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  if (
    !actionMutation.isError ||
    !matchesProjectAction(actionMutation, projectId, type)
  ) {
    return null;
  }
  return getErrorMessage(actionMutation.error);
}

export function resetProjectActionError(
  actionMutation: ProjectActionMutation,
  projectId: string,
  type: ProjectActionVariables["type"],
) {
  if (
    !actionMutation.isError ||
    !matchesProjectAction(actionMutation, projectId, type)
  ) {
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
