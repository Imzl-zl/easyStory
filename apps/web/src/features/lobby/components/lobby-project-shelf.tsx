"use client";

import { useState } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import type { ProjectActionVariables } from "@/features/lobby/components/lobby-project-model";
import {
  formatProjectTargetWords,
  formatProjectTrashDeadline,
  formatProjectTrashTime,
  resolveProjectActionButtonLabel,
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
    return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载项目列表...</div>;
  }
  if (error) {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {getErrorMessage(error)}
      </div>
    );
  }
  if (projects.length === 0) {
    return <ProjectShelfEmptyState deletedOnly={deletedOnly} />;
  }
  return (
    <div className="grid gap-4 md:grid-cols-2">
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
    <EmptyState
      title={deletedOnly ? "回收站为空" : "还没有项目"}
      description={
        deletedOnly
          ? "当前没有已删除项目。删除后的项目会先停留在这里，支持恢复或彻底删除。"
          : "先进入孵化器创建项目，再进入编辑器开始补设定和资产。"
      }
    />
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

  return (
    <article
      className={[
        "panel-shell flex flex-col gap-4 p-5",
        isDeleted
          ? "border-dashed bg-[linear-gradient(135deg,rgba(141,124,95,0.12),rgba(255,249,241,0.88))]"
          : "",
      ].join(" ")}
    >
      <ProjectCardHeader project={project} />
      <ProjectMetadataList project={project} templateName={templateName} />
      <ProjectActionRow
        actionMutation={actionMutation}
        onOpenDeleteDialog={() => setDeleteDialogOpen(true)}
        project={project}
      />
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

function ProjectCardHeader({ project }: Readonly<{ project: ProjectSummary }>) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="space-y-2">
        <h3 className="font-serif text-xl font-semibold text-[var(--text-primary)]">{project.name}</h3>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={project.status} />
          {project.deleted_at ? <StatusBadge label="回收站" status="archived" /> : null}
        </div>
      </div>
      <span className="text-xs uppercase tracking-[0.22em] text-[var(--text-secondary)]">
        {project.genre ?? "未设题材"}
      </span>
    </div>
  );
}

function ProjectMetadataList({
  project,
  templateName,
}: Readonly<{
  project: ProjectSummary;
  templateName: string;
}>) {
  return (
    <dl className="grid gap-2 text-sm text-[var(--text-secondary)]">
      <ProjectMetadataRow label="目标字数" value={formatProjectTargetWords(project.target_words)} />
      <ProjectMetadataRow label="模板" value={templateName} />
      <ProjectMetadataRow label="系统凭证池" value={project.allow_system_credential_pool ? "开启" : "关闭"} />
      {project.deleted_at ? (
        <>
          <ProjectMetadataRow label="删除时间" value={formatProjectTrashTime(project.deleted_at)} />
          <ProjectMetadataRow label="保留截止" value={formatProjectTrashDeadline(project.deleted_at)} />
        </>
      ) : null}
    </dl>
  );
}

function ProjectMetadataRow({
  label,
  value,
}: Readonly<{
  label: string;
  value: string;
}>) {
  return (
    <div className="flex justify-between gap-4">
      <dt>{label}</dt>
      <dd className="text-right text-[var(--text-primary)]">{value}</dd>
    </div>
  );
}

function ProjectActionRow({
  actionMutation,
  onOpenDeleteDialog,
  project,
}: Readonly<{
  actionMutation: ProjectActionMutation;
  onOpenDeleteDialog: () => void;
  project: ProjectSummary;
}>) {
  if (project.deleted_at) {
    return (
      <div className="flex flex-wrap gap-2">
        <button
          className="ink-button"
          disabled={actionMutation.isPending}
          onClick={() => actionMutation.mutate({ projectId: project.id, type: "restore" })}
          type="button"
        >
          {resolveProjectActionButtonLabel(
            "restore",
            isPendingProjectAction(actionMutation, project.id, "restore"),
          )}
        </button>
        <button className="ink-button-danger" disabled={actionMutation.isPending} onClick={onOpenDeleteDialog} type="button">
          {resolveProjectActionButtonLabel(
            "physicalDelete",
            isPendingProjectAction(actionMutation, project.id, "physicalDelete"),
          )}
        </button>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      <Link className="ink-button" href={`/workspace/project/${project.id}/studio?panel=setting`}>
        进入编辑器
      </Link>
      <Link className="ink-button-secondary" href={`/workspace/project/${project.id}/settings`}>
        项目设置
      </Link>
      <Link className="ink-button-secondary" href={`/workspace/project/${project.id}/engine`}>
        打开执行器
      </Link>
      <button
        className="ink-button-danger"
        disabled={actionMutation.isPending}
        onClick={() => actionMutation.mutate({ projectId: project.id, type: "delete" })}
        type="button"
      >
        {resolveProjectActionButtonLabel("delete", isPendingProjectAction(actionMutation, project.id, "delete"))}
      </button>
    </div>
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
