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
        <div className="w-8 h-8 border-2 border-line-soft border-t-accent-primary rounded-full animate-spin" />
        <p className="text-text-secondary text-[0.9rem]">正在加载作品列表…</p>
      </div>
    );
  }
  if (error) {
    return <div className="px-4.5 py-4 callout-danger text-accent-danger text-[0.92rem]">{getErrorMessage(error)}</div>;
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
    <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(300px,1fr))]">
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
    <div className="flex flex-col items-center justify-center py-24 px-6 rounded-3xl bg-muted border border-line-soft/60 text-center">
      <div className="flex w-16 h-16 items-center justify-center mb-5 rounded-2xl bg-accent-primary-soft text-accent-primary">
        <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
      </div>
      <h3 className="m-0 mb-2 text-text-primary font-serif text-[1.25rem] font-semibold tracking-[-0.03em]">
        {deletedOnly ? "回收站为空" : "还没有作品"}
      </h3>
      <p className="max-w-[24rem] m-0 text-text-secondary text-[0.9rem] leading-relaxed">
        {deletedOnly
          ? "当前没有已删除项目。删除后的项目会保留在回收站里，随时可以恢复。"
          : "新建作品后，它会作为一张书卡出现在这里，直接回到创作现场。"}
      </p>
      {!deletedOnly && (
        <Link
          className="ink-button mt-6"
          href="/workspace/lobby/new"
        >
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
      className={`group flex items-center gap-4 px-4 py-3.5 rounded-2xl bg-surface border border-transparent transition-all hover:border-line-soft hover:shadow-sm ${isDeleted ? "opacity-60" : ""}`}
      style={
        {
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
          <h3 className="m-0 min-w-0 text-text-primary text-[0.95rem] font-semibold tracking-[-0.02em] truncate">
            {project.name}
          </h3>
          <StatusBadge status={project.status} />
          {isDeleted && <StatusBadge label="回收站" status="archived" />}
        </div>
        <div className="flex items-center gap-3 text-text-tertiary text-[0.76rem]">
          <span>{project.genre ?? "未定题材"}</span>
          <span className="w-px h-3 bg-line-soft" />
          <span>{formatProjectTargetWords(project.target_words)}</span>
          <span className="w-px h-3 bg-line-soft" />
          <span>{templateName === "无" ? "自由创作" : templateName}</span>
        </div>
      </div>

      {/* 时间 */}
      <span className="hidden md:block text-text-tertiary text-[0.76rem] whitespace-nowrap [font-variant-numeric:tabular-nums]">
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
              className="ink-icon-button text-accent-danger hover:text-accent-danger hover:bg-accent-danger/10"
              disabled={actionMutation.isPending}
              onClick={handleOpenSoftDeleteDialog}
              type="button"
              title="移入回收站"
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
      className={`group flex min-w-0 flex-col overflow-hidden rounded-2xl bg-surface border border-line-soft/60 transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-line-strong/40 ${isDeleted ? "opacity-60" : ""}`}
      style={
        {
          "--project-card-accent": tone.accent,
          "--project-card-surface": tone.surface,
        } as CSSProperties
      }
    >
      {/* 顶部颜色条 */}
      <div
        className="h-[3px] shrink-0"
        style={{ background: `linear-gradient(to right, ${tone.accent}, ${tone.accent}40, transparent)` }}
      />

      <div className="grid gap-2.5 p-5 pb-3 flex-1">
        {/* 标题行 */}
        <div className="flex items-center gap-3 min-w-0">
          <span
            className="flex w-9 h-9 shrink-0 items-center justify-center rounded-xl font-serif text-[1.1rem] font-semibold"
            style={{ background: `${tone.accent}18`, color: tone.accent }}
          >
            {project.name.charAt(0)}
          </span>
          <h3 className="m-0 min-w-0 text-text-primary font-serif text-[1.15rem] font-semibold tracking-[-0.03em] leading-tight truncate">
            {project.name}
          </h3>
          {!project.deleted_at ? (
            <Link
              className="inline-flex w-7 h-7 shrink-0 items-center justify-center rounded-lg text-text-tertiary transition-all hover:bg-muted hover:text-text-secondary ml-auto"
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
          <span className="inline-flex items-center h-[1.3rem] px-[0.5rem] rounded-full bg-muted text-text-secondary text-[0.7rem] font-medium">
            {project.genre ?? "未定题材"}
          </span>
          <span className="inline-flex items-center h-[1.3rem] px-[0.5rem] rounded-full bg-muted text-text-secondary text-[0.7rem] font-medium">
            {formatProjectTargetWords(project.target_words)}
          </span>
        </div>

        {/* 描述 */}
        <p className="m-0 text-text-secondary text-[0.85rem] leading-relaxed">
          {isDeleted
            ? `项目已移入回收站，保留到 ${formatProjectTrashDeadline(project.deleted_at)}。`
            : `以 ${templateName === "无" ? "自由创作" : templateName} 为起点，继续整理设定、章节和正文。`}
        </p>

        {/* 元信息 */}
        <div className="flex flex-wrap gap-[0.5rem_0.7rem] text-text-tertiary text-[0.74rem] leading-relaxed">
          <span>模板 · {templateName}</span>
          <span>{project.allow_system_credential_pool ? "允许系统模型池" : "使用自选连接"}</span>
        </div>
      </div>

      {/* 底部操作栏 */}
      <div className="flex items-center justify-between gap-4 px-5 pb-4 pt-3 border-t border-line-soft/60">
        <span className="text-text-tertiary text-[0.74rem] leading-relaxed [font-variant-numeric:tabular-nums]">
          {isDeleted
            ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
            : `最近更新 ${formatProjectUpdatedTime(project.updated_at)}`}
        </span>
        <div className="flex flex-wrap gap-2 items-center justify-end">
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
                彻底删除
              </button>
            </>
          ) : (
            <>
              <Link className="ink-button text-[0.8rem] h-8 px-3" href={`/workspace/project/${project.id}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}>
                继续创作
              </Link>
              <button
                className="ink-button-danger text-[0.8rem] h-8 px-3"
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
