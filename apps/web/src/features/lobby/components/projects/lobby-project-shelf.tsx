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
};

export function LobbyProjectShelf({
  actionMutation,
  deletedOnly,
  error,
  isLoading,
  projects,
  templateNameById,
}: Readonly<LobbyProjectShelfProps>) {
  if (isLoading) {
    return <div className="py-10 px-4 text-text-secondary text-[0.95rem] text-center">正在加载项目列表…</div>;
  }
  if (error) {
    return <div className="px-4.5 py-4 callout-danger text-accent-danger text-[0.92rem]">{getErrorMessage(error)}</div>;
  }
  if (projects.length === 0) {
    return <ProjectShelfEmptyState deletedOnly={deletedOnly} />;
  }

  return (
    <div className="grid gap-5 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">
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
    <div className="flex flex-col items-center justify-center py-24 px-6 rounded-5xl bg-muted shadow-[inset_0_0_0_1px_var(--line-soft)] text-center">
      <div className="flex w-[4.2rem] h-[4.2rem] items-center justify-center mb-4 rounded-2xl bg-accent-soft text-accent-primary">
        <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
      </div>
      <h3 className="m-0 mb-1 text-text-primary font-serif text-[1.35rem] font-semibold tracking-[-0.04em]">{deletedOnly ? "回收站为空" : "还没有作品"}</h3>
      <p className="max-w-[26rem] m-0 text-text-secondary text-[0.92rem] leading-relaxed">
        {deletedOnly
          ? "当前没有已删除项目。删除后的项目会保留在回收站里，随时可以恢复。"
          : "新建作品后，它会作为一张书卡出现在这里，直接回到创作现场。"}
      </p>
    </div>
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
      className={`group flex min-w-0 flex-col overflow-hidden rounded-3xl bg-[var(--project-card-surface,rgba(255,253,251,0.92))] shadow-md transition-all hover:-translate-y-0.5 hover:shadow-lg ${isDeleted ? "bg-glass-heavy" : ""}`}
      style={
        {
          "--project-card-accent": tone.accent,
          "--project-card-surface": tone.surface,
        } as CSSProperties
      }
    >
      {/* Accent gradient strip */}
      <div
        className="h-[3px] shrink-0"
        style={{ background: `linear-gradient(to right, ${tone.accent}, ${tone.accent}40, transparent)` }}
      />

      <div className="grid gap-2.5 p-5 pb-3 flex-1">
        {/* Title row: avatar + name + settings */}
        <div className="flex items-center gap-3 min-w-0">
          <span
            className="flex w-9 h-9 shrink-0 items-center justify-center rounded-xl font-serif text-[1.15rem] font-semibold"
            style={{ background: `${tone.accent}18`, color: tone.accent }}
          >
            {project.name.charAt(0)}
          </span>
          <h3 className="m-0 min-w-0 text-text-primary font-serif text-[1.3rem] font-semibold tracking-[-0.03em] leading-tight truncate">
            {project.name}
          </h3>
          {!project.deleted_at ? (
            <Link
              className="inline-flex w-7 h-7 shrink-0 items-center justify-center rounded-lg text-text-tertiary transition-all hover:bg-muted hover:text-text-secondary"
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

        {/* Badges */}
        <div className="flex flex-wrap gap-[0.4rem] items-center">
          <StatusBadge status={project.status} />
          {isDeleted ? <StatusBadge label="回收站" status="archived" /> : null}
          <span className="inline-flex items-center h-[1.35rem] px-[0.55rem] rounded-full bg-muted shadow-xs text-text-secondary text-[0.72rem] font-medium">{project.genre ?? "未定题材"}</span>
          <span className="inline-flex items-center h-[1.35rem] px-[0.55rem] rounded-full bg-muted shadow-xs text-text-secondary text-[0.72rem] font-medium">{formatProjectTargetWords(project.target_words)}</span>
        </div>

        {/* Description */}
        <p className="m-0 text-text-secondary text-[0.88rem] leading-relaxed">
          {isDeleted
            ? `项目已移入回收站，保留到 ${formatProjectTrashDeadline(project.deleted_at)}。`
            : `以 ${templateName === "无" ? "自由创作" : templateName} 为起点，继续整理设定、章节和正文。`}
        </p>

        {/* Meta */}
        <div className="flex flex-wrap gap-[0.55rem_0.8rem] text-text-tertiary text-[0.76rem] leading-relaxed">
          <span>模板 · {templateName}</span>
          <span>{project.allow_system_credential_pool ? "允许系统模型池" : "使用自选连接"}</span>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between gap-4 px-5 pb-4 pt-3 border-t border-[var(--line-soft)]">
        <span className="text-text-tertiary text-[0.76rem] leading-relaxed [font-variant-numeric:tabular-nums]">
          {isDeleted
            ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
            : `最近更新 ${formatProjectUpdatedTime(project.updated_at)}`}
        </span>
        <div className="flex flex-wrap gap-2 items-center justify-end">
          {isDeleted ? (
            <>
              <button
                className="ink-button"
                disabled={actionMutation.isPending}
                onClick={() => actionMutation.mutate({ projectId: project.id, type: "restore" })}
                type="button"
              >
                恢复
              </button>
              <button
                className="ink-button-danger"
                disabled={actionMutation.isPending}
                onClick={handleOpenPhysicalDeleteDialog}
                type="button"
              >
                彻底删除
              </button>
            </>
          ) : (
            <>
              <Link className="ink-button" href={`/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}>
                继续创作
              </Link>
              <button
                className="ink-button-danger"
                disabled={actionMutation.isPending}
                onClick={handleOpenSoftDeleteDialog}
                type="button"
              >
                删除
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
