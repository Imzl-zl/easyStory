"use client";

import { useState } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { InkStatusBadge, isPendingProjectAction, resetProjectActionError, resolveProjectActionErrorMessage } from "@/features/lobby/components/projects/lobby-project-card";
import type { ProjectActionVariables } from "@/features/lobby/components/projects/lobby-project-model";
import {
  formatProjectTargetWords,
  formatProjectTrashTime,
  formatProjectUpdatedTime,
  resolveProjectCardTone,
} from "@/features/lobby/components/projects/lobby-project-support";
import {
  ProjectDeleteConfirmDialog,
  RecycleBinDeleteDialog,
} from "@/features/lobby/components/recycle-bin/recycle-bin-dialogs";
import type { ProjectDetail, ProjectSummary } from "@/lib/api/types";

type ProjectActionMutation = UseMutationResult<
  ProjectDetail | void,
  unknown,
  ProjectActionVariables
>;

export function LobbyProjectListItem({
  actionMutation,
  project,
}: {
  actionMutation: ProjectActionMutation;
  project: ProjectSummary;
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

  const studioHref = `/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`;

  const handleEnterStudio = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    setIsEntering(true);
    setTimeout(() => {
      router.push(studioHref);
    }, 420);
  };

  const itemClasses = [
    "lobby-project-list-item",
    isDeleted ? "lobby-project-list-item--deleted" : "",
    isEntering ? "lobby-project-list-item--entering" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={itemClasses}>
      <div
        className="lobby-project-list-item__accent-bar"
        style={{ background: tone.accent }}
      />

      <span
        className="lobby-project-list-item__seal"
        style={{
          background: `${tone.accent}12`,
          color: tone.accent,
        }}
      >
        {project.name.charAt(0)}
      </span>

      <div className="lobby-project-list-item__body">
        <div className="lobby-project-list-item__title-row">
          <h3 className="lobby-project-list-item__title truncate">
            {project.name}
          </h3>
          <InkStatusBadge status={project.status} />
          {isDeleted ? <InkStatusBadge status="archived" /> : null}
        </div>
        <div className="lobby-project-list-item__meta">
          <span>{project.genre ?? "未定题材"}</span>
          <span style={{ color: "var(--line-medium)" }}>·</span>
          <span>{formatProjectTargetWords(project.target_words)}</span>
        </div>
      </div>

      <span className="lobby-project-list-item__timestamp hidden md:block">
        {isDeleted
          ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
          : `更新于 ${formatProjectUpdatedTime(project.updated_at)}`}
      </span>

      <div className="lobby-project-list-item__actions">
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
                background: `${tone.accent}12`,
                color: tone.accent,
                border: `1px solid ${tone.accent}25`,
              }}
            >
              展卷
            </Link>
            <Link
              className="ink-icon-button"
              href={`/workspace/project/${project.id}/engine`}
              title="工作流"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
