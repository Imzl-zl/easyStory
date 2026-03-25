"use client";

import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import type { ProjectActionVariables } from "@/features/lobby/components/lobby-project-model";
import { getErrorMessage } from "@/lib/api/client";
import type { ProjectDetail, ProjectSummary } from "@/lib/api/types";

type LobbyProjectShelfProps = {
  actionMutation: UseMutationResult<ProjectDetail, unknown, ProjectActionVariables>;
  projects: ProjectSummary[];
  isLoading: boolean;
  error: unknown;
  deletedOnly: boolean;
  templateNameById: Map<string, string>;
};

export function LobbyProjectShelf({
  actionMutation,
  projects,
  isLoading,
  error,
  deletedOnly,
  templateNameById,
}: LobbyProjectShelfProps) {
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
    return (
      <EmptyState
        title={deletedOnly ? "回收站为空" : "还没有项目"}
        description={
          deletedOnly
            ? "当前没有已删除项目。"
            : "先进入 Incubator 创建项目，再进入 Studio 开始补设定和资产。"
        }
      />
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {projects.map((project) => (
        <LobbyProjectCard
          key={project.id}
          actionMutation={actionMutation}
          project={project}
          templateName={project.template_id ? templateNameById.get(project.template_id) ?? "已绑定模板" : "无"}
        />
      ))}
    </div>
  );
}

function LobbyProjectCard({
  actionMutation,
  project,
  templateName,
}: {
  actionMutation: UseMutationResult<ProjectDetail, unknown, ProjectActionVariables>;
  project: ProjectSummary;
  templateName: string;
}) {
  return (
    <article className="panel-shell flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <h3 className="font-serif text-xl font-semibold">{project.name}</h3>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={project.status} />
            {project.deleted_at ? <StatusBadge label="trashed" status="archived" /> : null}
          </div>
        </div>
        <span className="text-xs uppercase tracking-[0.22em] text-[var(--text-secondary)]">
          {project.genre ?? "未设题材"}
        </span>
      </div>
      <dl className="grid gap-2 text-sm text-[var(--text-secondary)]">
        <div className="flex justify-between gap-4">
          <dt>目标字数</dt>
          <dd>{project.target_words ?? "未设定"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>模板</dt>
          <dd>{templateName}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>系统凭证池</dt>
          <dd>{project.allow_system_credential_pool ? "开启" : "关闭"}</dd>
        </div>
      </dl>
      <div className="flex flex-wrap gap-2">
        {!project.deleted_at ? (
          <>
            <Link className="ink-button" href={`/workspace/project/${project.id}/studio?panel=setting`}>
              进入 Studio
            </Link>
            <Link className="ink-button-secondary" href={`/workspace/project/${project.id}/engine`}>
              打开 Engine
            </Link>
            <button
              className="ink-button-danger"
              disabled={actionMutation.isPending}
              onClick={() => actionMutation.mutate({ projectId: project.id, type: "delete" })}
              type="button"
            >
              移入回收站
            </button>
          </>
        ) : (
          <button
            className="ink-button"
            disabled={actionMutation.isPending}
            onClick={() => actionMutation.mutate({ projectId: project.id, type: "restore" })}
            type="button"
          >
            恢复项目
          </button>
        )}
      </div>
    </article>
  );
}
