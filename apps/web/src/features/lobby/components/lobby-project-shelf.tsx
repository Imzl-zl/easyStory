"use client";

import { useState, type CSSProperties } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";

import { StatusBadge } from "@/components/ui/status-badge";
import type { ProjectActionVariables } from "@/features/lobby/components/lobby-project-model";
import {
  formatProjectTargetWords,
  formatProjectTrashDeadline,
  formatProjectTrashTime,
  formatProjectUpdatedTime,
  resolveProjectCardTone,
} from "@/features/lobby/components/lobby-project-support";
import { RecycleBinDeleteDialog } from "@/features/lobby/components/recycle-bin-dialogs";
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
    return <div className="py-10 px-4 text-[var(--text-secondary)] text-[0.95rem] text-center">正在加载项目列表…</div>;
  }
  if (error) {
    return <div className="px-4.5 py-4 rounded-[22px] bg-[rgba(196,90,90,0.08)] text-[var(--accent-danger)] text-[0.92rem]">{getErrorMessage(error)}</div>;
  }
  if (projects.length === 0) {
    return <ProjectShelfEmptyState deletedOnly={deletedOnly} />;
  }

  return (
    <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">
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
    <div className="flex flex-col items-center justify-center py-24 px-6 rounded-[28px] bg-[rgba(255,255,255,0.62)] shadow-[inset_0_0_0_1px_rgba(61,61,61,0.06)] text-center">
      <div className="flex w-[4.2rem] h-[4.2rem] items-center justify-center mb-4 rounded-5 bg-[rgba(90,122,107,0.08)] text-[var(--accent-primary)]">
        <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
      </div>
      <h3 className="m-0 mb-1 text-[var(--text-primary)] font-serif text-[1.35rem] font-semibold tracking-[-0.04em]">{deletedOnly ? "回收站为空" : "还没有作品"}</h3>
      <p className="max-w-[26rem] m-0 text-[var(--text-secondary)] text-[0.92rem] leading-relaxed">
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
  const isDeleted = Boolean(project.deleted_at);
  const isPhysicalDeleting = isPendingProjectAction(actionMutation, project.id, "physicalDelete");
  const tone = resolveProjectCardTone(project.id);

  return (
    <article
      className={`flex min-w-0 flex-col overflow-hidden rounded-[28px] bg-[var(--project-card-surface,rgba(255,253,251,0.92))] shadow-[inset_0_0_0_1px_rgba(61,61,61,0.07),0_14px_28px_-24px_rgba(61,61,61,0.32)] transition-all hover:-translate-y-0.5 hover:shadow-[inset_0_0_0_1px_rgba(61,61,61,0.09),0_18px_30px_-24px_rgba(61,61,61,0.28)] ${isDeleted ? "bg-[rgba(248,246,241,0.92)]" : ""}`}
      style={
        {
          "--project-card-accent": tone.accent,
          "--project-card-surface": tone.surface,
        } as CSSProperties
      }
    >
      <div className="flex min-h-[104px] items-start justify-between gap-3 p-4 pt-4 pb-[0.95rem] bg-[var(--project-card-accent,var(--accent-primary))] text-[rgba(255,255,255,0.94)]">
        <div className="grid gap-0.5">
          <span className="text-[0.68rem] font-semibold tracking-[0.14em] uppercase opacity-88">{project.genre ?? "未定题材"}</span>
          <span className="font-serif text-[2.3rem] font-semibold tracking-[-0.06em] leading-none">{project.name.charAt(0)}</span>
        </div>
        {!project.deleted_at ? (
          <Link className="inline-flex w-8 h-8 items-center justify-center rounded-full bg-[rgba(255,255,255,0.14)] text-[rgba(255,255,255,0.96)] transition-all hover:bg-[rgba(255,255,255,0.22)] hover:-translate-y-px" href={`/workspace/project/${project.id}/settings`} title="项目设置">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </Link>
        ) : null}
      </div>

      <div className="grid flex-1 gap-3 p-4 px-[1.15rem] pb-[0.85rem]">
        <div className="flex flex-wrap gap-[0.45rem] items-center">
          <StatusBadge status={project.status} />
          {isDeleted ? <StatusBadge label="回收站" status="archived" /> : null}
          <span className="inline-flex items-center h-6 px-[0.65rem] rounded-full bg-[rgba(255,255,255,0.72)] text-[var(--text-secondary)] text-[0.74rem] font-medium">{formatProjectTargetWords(project.target_words)}</span>
        </div>
        <h3 className="m-0 text-[var(--text-primary)] font-serif text-[1.42rem] font-semibold tracking-[-0.04em] leading-tight">{project.name}</h3>
        <p className="m-0 text-[var(--text-secondary)] text-[0.92rem] leading-relaxed">
          {isDeleted
            ? `项目已移入回收站，保留到 ${formatProjectTrashDeadline(project.deleted_at)}。`
            : `以 ${templateName === "无" ? "自由创作" : templateName} 为起点，继续整理设定、章节和正文。`}
        </p>
        <div className="flex flex-wrap gap-[0.55rem_0.8rem] text-[var(--text-tertiary)] text-[0.78rem] leading-relaxed">
          <span>模板 · {templateName}</span>
          <span>{project.allow_system_credential_pool ? "允许系统模型池" : "使用自选连接"}</span>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4 pt-[0.95rem] px-[1.15rem] pb-[1.15rem]">
        <span className="text-[var(--text-tertiary)] text-[0.78rem] leading-relaxed [font-variant-numeric:tabular-nums]">
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
                onClick={() => setDeleteDialogOpen(true)}
                type="button"
              >
                彻底删除
              </button>
            </>
          ) : (
            <>
              <Link className="ink-button" href={`/workspace/project/${project.id}/studio?panel=setting`}>
                继续创作
              </Link>
              <button
                className="ink-button-danger"
                disabled={actionMutation.isPending}
                onClick={() => actionMutation.mutate({ projectId: project.id, type: "delete" })}
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
          isPending={isPhysicalDeleting}
          onClose={() => setDeleteDialogOpen(false)}
          onConfirm={() => actionMutation.mutate({ projectId: project.id, type: "physicalDelete" })}
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
  return (
    actionMutation.isPending &&
    actionMutation.variables?.projectId === projectId &&
    actionMutation.variables?.type === type
  );
}
