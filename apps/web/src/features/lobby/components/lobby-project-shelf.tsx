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
import styles from "./lobby-project-shelf.module.css";

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
    return <div className={styles.loading}>正在加载项目列表…</div>;
  }
  if (error) {
    return <div className={styles.error}>{getErrorMessage(error)}</div>;
  }
  if (projects.length === 0) {
    return <ProjectShelfEmptyState deletedOnly={deletedOnly} />;
  }

  return (
    <div className={styles.cardGrid}>
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
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
      </div>
      <h3 className={styles.emptyTitle}>{deletedOnly ? "回收站为空" : "还没有作品"}</h3>
      <p className={styles.emptyDescription}>
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
      className={[styles.card, isDeleted ? styles.deletedCard : ""].join(" ")}
      style={
        {
          "--project-card-accent": tone.accent,
          "--project-card-surface": tone.surface,
        } as CSSProperties
      }
    >
      <div className={styles.cardCoverBand}>
        <div className={styles.cardCoverMeta}>
          <span className={styles.cardCoverEyebrow}>{project.genre ?? "未定题材"}</span>
          <span className={styles.cardCoverGlyph}>{project.name.charAt(0)}</span>
        </div>
        {!project.deleted_at ? (
          <Link className={styles.cardActionButton} href={`/workspace/project/${project.id}/settings`} title="项目设置">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </Link>
        ) : null}
      </div>

      <div className={styles.cardBody}>
        <div className={styles.cardStatusRow}>
          <StatusBadge status={project.status} />
          {isDeleted ? <StatusBadge label="回收站" status="archived" /> : null}
          <span className={styles.cardMetaPill}>{formatProjectTargetWords(project.target_words)}</span>
        </div>
        <h3 className={styles.cardTitle}>{project.name}</h3>
        <p className={styles.cardDescription}>
          {isDeleted
            ? `项目已移入回收站，保留到 ${formatProjectTrashDeadline(project.deleted_at)}。`
            : `以 ${templateName === "无" ? "自由创作" : templateName} 为起点，继续整理设定、章节和正文。`}
        </p>
        <div className={styles.cardDetailRow}>
          <span>模板 · {templateName}</span>
          <span>{project.allow_system_credential_pool ? "允许系统模型池" : "使用自选连接"}</span>
        </div>
      </div>

      <div className={styles.cardFooter}>
        <span className={styles.cardTime}>
          {isDeleted
            ? `删除于 ${formatProjectTrashTime(project.deleted_at)}`
            : `最近更新 ${formatProjectUpdatedTime(project.updated_at)}`}
        </span>
        <div className={styles.cardActions}>
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
