"use client";

import { useDeferredValue, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { CredentialCenter } from "@/features/settings/components/credential-center";
import { getErrorMessage } from "@/lib/api/client";
import { deleteProject, listProjects, restoreProject } from "@/lib/api/projects";
import { listTemplates } from "@/lib/api/templates";
import type { ProjectDetail, ProjectSummary } from "@/lib/api/types";

type ProjectActionVariables = {
  projectId: string;
  type: "delete" | "restore";
};

export function LobbyPage() {
  const queryClient = useQueryClient();
  const [showRecycleBin, setShowRecycleBin] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const deferredSearchText = useDeferredValue(searchText);
  const projectsQuery = useQuery({
    queryKey: ["projects", showRecycleBin],
    queryFn: () => listProjects(showRecycleBin),
  });
  const templatesQuery = useQuery({ queryKey: ["templates"], queryFn: listTemplates });
  const actionMutation = useMutation({
    mutationFn: ({ projectId, type }: { projectId: string; type: "delete" | "restore" }) =>
      type === "delete" ? deleteProject(projectId) : restoreProject(projectId),
    onSuccess: async () => {
      setFeedback("项目状态已更新。");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });
  const filteredProjects = buildFilteredProjects(projectsQuery.data, deferredSearchText);
  const templateNameById = new Map((templatesQuery.data ?? []).map((template) => [template.id, template.name]));
  const templatePreviewNames = (templatesQuery.data ?? []).slice(0, 3).map((template) => template.name);

  return (
    <div className="space-y-6">
      <SectionCard
        title="Lobby"
        description="项目书架只负责浏览、筛选与恢复；新建流程统一从独立 Incubator 进入。"
        action={<LobbyToolbar onToggleRecycleBin={() => setShowRecycleBin((value) => !value)} onToggleSettings={() => setShowSettings((value) => !value)} showRecycleBin={showRecycleBin} showSettings={showSettings} />}
      >
        <div className="grid gap-6 xl:grid-cols-[0.72fr_1.28fr]">
          <div className="space-y-4">
            <IncubatorEntryCard
              feedback={feedback}
              templatesLoading={templatesQuery.isLoading}
              templateCount={templatesQuery.data?.length ?? 0}
              templatePreviewNames={templatePreviewNames}
              templatesError={templatesQuery.error ? getErrorMessage(templatesQuery.error) : null}
            />
            <label className="block">
              <span className="label-text">快速搜索</span>
              <input
                className="ink-input"
                placeholder="按项目名过滤"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
              />
            </label>
          </div>
          <ProjectShelf
            actionMutation={actionMutation}
            filteredProjects={filteredProjects}
            isLoading={projectsQuery.isLoading}
            projectsError={projectsQuery.error ? getErrorMessage(projectsQuery.error) : null}
            showRecycleBin={showRecycleBin}
            templateNameById={templateNameById}
          />
        </div>
      </SectionCard>
      {showSettings ? <CredentialCenter /> : null}
    </div>
  );
}

function LobbyToolbar({
  showSettings,
  showRecycleBin,
  onToggleSettings,
  onToggleRecycleBin,
}: {
  showSettings: boolean;
  showRecycleBin: boolean;
  onToggleSettings: () => void;
  onToggleRecycleBin: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button className="ink-button-secondary" onClick={onToggleSettings} type="button">
        {showSettings ? "关闭设置" : "全局设置"}
      </button>
      <button className="ink-button-secondary" onClick={onToggleRecycleBin} type="button">
        {showRecycleBin ? "返回项目列表" : "打开回收站"}
      </button>
    </div>
  );
}

function IncubatorEntryCard({
  feedback,
  templatesLoading,
  templateCount,
  templatePreviewNames,
  templatesError,
}: {
  feedback: string | null;
  templatesLoading: boolean;
  templateCount: number;
  templatePreviewNames: string[];
  templatesError: string | null;
}) {
  return (
    <section className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">Incubator</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          模板问答、自由描述和模板建项目已经独立出来，Lobby 不再内联承担创建状态。
        </p>
      </div>
      <dl className="grid gap-3 text-sm text-[var(--text-secondary)]">
        <div className="flex justify-between gap-4">
          <dt>可用模板</dt>
          <dd>{templatesLoading ? "加载中..." : templateCount}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>推荐入口</dt>
          <dd>模板问答 / 自由描述</dd>
        </div>
      </dl>
      {templatePreviewNames.length > 0 ? (
        <p className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
          最近可用模板：{templatePreviewNames.join(" / ")}
        </p>
      ) : null}
      {templatesError ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {templatesError}
        </div>
      ) : null}
      {feedback ? (
        <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
          {feedback}
        </div>
      ) : null}
      <Link className="ink-button w-full justify-center" href="/workspace/lobby/new">
        进入 Incubator
      </Link>
    </section>
  );
}

function ProjectShelf({
  actionMutation,
  filteredProjects,
  isLoading,
  projectsError,
  showRecycleBin,
  templateNameById,
}: {
  actionMutation: UseMutationResult<ProjectDetail, unknown, ProjectActionVariables>;
  filteredProjects: ProjectSummary[];
  isLoading: boolean;
  projectsError: string | null;
  showRecycleBin: boolean;
  templateNameById: Map<string, string>;
}) {
  if (isLoading) {
    return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载项目列表...</div>;
  }
  if (projectsError) {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {projectsError}
      </div>
    );
  }
  if (filteredProjects.length === 0) {
    return (
      <EmptyState
        title={showRecycleBin ? "回收站为空" : "还没有项目"}
        description={
          showRecycleBin
            ? "当前没有已删除项目。"
            : "先进入 Incubator 创建项目，再进入 Studio 开始补设定和资产。"
        }
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {filteredProjects.map((project) => (
        <ProjectCard
          key={project.id}
          actionMutation={actionMutation}
          project={project}
          templateName={project.template_id ? templateNameById.get(project.template_id) ?? "已绑定模板" : "无"}
        />
      ))}
    </div>
  );
}

function ProjectCard({
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

function buildFilteredProjects(projects: ProjectSummary[] | undefined, keyword: string): ProjectSummary[] {
  const normalizedKeyword = keyword.trim().toLowerCase();
  if (!normalizedKeyword) {
    return projects ?? [];
  }
  return (projects ?? []).filter((project) => project.name.toLowerCase().includes(normalizedKeyword));
}
