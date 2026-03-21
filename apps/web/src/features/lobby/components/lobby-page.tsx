"use client";

import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { CredentialCenter } from "@/features/settings/components/credential-center";
import { getErrorMessage } from "@/lib/api/client";
import { createProject, deleteProject, listProjects, restoreProject } from "@/lib/api/projects";
import { listTemplates } from "@/lib/api/templates";

export function LobbyPage() {
  const queryClient = useQueryClient();
  const [showRecycleBin, setShowRecycleBin] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [searchText, setSearchText] = useState("");
  const deferredSearchText = useDeferredValue(searchText);
  const [projectName, setProjectName] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects", showRecycleBin],
    queryFn: () => listProjects(showRecycleBin),
  });
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: listTemplates,
  });

  useEffect(() => {
    const templates = templatesQuery.data ?? [];
    if (templates.length === 0) {
      return;
    }
    if (selectedTemplateId && templates.some((template) => template.id === selectedTemplateId)) {
      return;
    }
    startTransition(() => {
      setSelectedTemplateId(templates[0].id);
    });
  }, [selectedTemplateId, templatesQuery.data]);

  const filteredProjects = useMemo(() => {
    const keyword = deferredSearchText.trim().toLowerCase();
    if (!keyword) {
      return projectsQuery.data ?? [];
    }
    return (projectsQuery.data ?? []).filter((project) =>
      project.name.toLowerCase().includes(keyword),
    );
  }, [deferredSearchText, projectsQuery.data]);
  const templateNameById = useMemo(
    () => new Map((templatesQuery.data ?? []).map((template) => [template.id, template.name])),
    [templatesQuery.data],
  );
  const selectedTemplate =
    templatesQuery.data?.find((template) => template.id === selectedTemplateId) ?? null;

  const refreshProjects = () =>
    queryClient.invalidateQueries({
      queryKey: ["projects"],
    });

  const createMutation = useMutation({
    mutationFn: () =>
      createProject({
        name: projectName.trim(),
        template_id: selectedTemplateId || null,
      }),
    onSuccess: () => {
      setProjectName("");
      if (templatesQuery.data?.length) {
        setSelectedTemplateId(templatesQuery.data[0].id);
      } else {
        setSelectedTemplateId("");
      }
      setFeedback("项目已创建。");
      refreshProjects();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });
  const canSubmit =
    projectName.trim().length > 0 &&
    !createMutation.isPending &&
    (templatesQuery.data?.length ? Boolean(selectedTemplateId) : true);

  const actionMutation = useMutation({
    mutationFn: async ({
      type,
      projectId,
    }: {
      type: "delete" | "restore";
      projectId: string;
    }) => {
      if (type === "delete") {
        return deleteProject(projectId);
      }
      return restoreProject(projectId);
    },
    onSuccess: () => {
      setFeedback("项目状态已更新。");
      refreshProjects();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  return (
    <div className="space-y-6">
      <SectionCard
        title="Lobby"
        description="项目书架保持安静、稳定和可恢复。删除动作只进回收站，不暴露永久删除。"
        action={
          <div className="flex flex-wrap gap-2">
            <button className="ink-button-secondary" onClick={() => setShowSettings((value) => !value)}>
              {showSettings ? "关闭设置" : "全局设置"}
            </button>
            <button
              className="ink-button-secondary"
              onClick={() => setShowRecycleBin((value) => !value)}
            >
              {showRecycleBin ? "返回项目列表" : "打开回收站"}
            </button>
          </div>
        }
      >
        <div className="grid gap-6 xl:grid-cols-[0.76fr_1.24fr]">
          <form
            className="panel-muted space-y-4 p-5"
            onSubmit={(event) => {
              event.preventDefault();
              setFeedback(null);
              createMutation.mutate();
            }}
          >
            <div className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">Incubator</h3>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
                当前新建流程先收口为基础信息，再进入 `Studio` 继续补设定。
              </p>
            </div>

            <label className="block">
              <span className="label-text">项目名称</span>
              <input
                className="ink-input"
                maxLength={255}
                minLength={1}
                required
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
              />
            </label>

            <label className="block">
              <span className="label-text">创作模板</span>
              <select
                className="ink-input"
                disabled={templatesQuery.isLoading || templatesQuery.data?.length === 0}
                value={selectedTemplateId}
                onChange={(event) => setSelectedTemplateId(event.target.value)}
              >
                {templatesQuery.isLoading ? (
                  <option value="">模板加载中...</option>
                ) : null}
                {!templatesQuery.isLoading && (templatesQuery.data?.length ?? 0) === 0 ? (
                  <option value="">当前无可用模板，将创建基础项目</option>
                ) : null}
                {(templatesQuery.data ?? []).map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                    {template.genre ? ` · ${template.genre}` : ""}
                  </option>
                ))}
              </select>
            </label>

            {selectedTemplate ? (
              <div className="rounded-3xl border border-[rgba(19,19,18,0.08)] bg-[rgba(255,255,255,0.54)] px-4 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-serif text-base font-semibold">{selectedTemplate.name}</p>
                    <p className="text-sm leading-6 text-[var(--text-secondary)]">
                      {selectedTemplate.description ?? "当前模板未提供额外说明。"}
                    </p>
                  </div>
                  <span className="text-xs uppercase tracking-[0.22em] text-[var(--text-secondary)]">
                    {selectedTemplate.genre ?? "通用"}
                  </span>
                </div>
                <dl className="mt-4 grid gap-2 text-sm text-[var(--text-secondary)]">
                  <div className="flex justify-between gap-4">
                    <dt>默认工作流</dt>
                    <dd>{selectedTemplate.workflow_id ?? "未配置"}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt>节点数量</dt>
                    <dd>{selectedTemplate.node_count}</dd>
                  </div>
                </dl>
              </div>
            ) : null}

            <label className="block">
              <span className="label-text">快速搜索</span>
              <input
                className="ink-input"
                placeholder="按项目名过滤"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
              />
            </label>

            {templatesQuery.error ? (
              <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
                {getErrorMessage(templatesQuery.error)}
              </div>
            ) : null}

            {feedback ? (
              <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
                {feedback}
              </div>
            ) : null}

            <button className="ink-button w-full" disabled={!canSubmit} type="submit">
              {createMutation.isPending ? "创建中..." : "创建项目"}
            </button>
          </form>

          <div className="space-y-4">
            {projectsQuery.isLoading ? (
              <p className="text-sm text-[var(--text-secondary)]">正在加载项目列表...</p>
            ) : null}
            {projectsQuery.error ? (
              <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
                {getErrorMessage(projectsQuery.error)}
              </div>
            ) : null}

            {filteredProjects.length === 0 ? (
              <EmptyState
                title={showRecycleBin ? "回收站为空" : "还没有项目"}
                description={
                  showRecycleBin
                    ? "当前没有已删除项目。"
                    : "先在左侧创建你的第一部作品，再进入 Studio 开始补设定和资产。"
                }
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {filteredProjects.map((project) => (
                  <article key={project.id} className="panel-shell flex flex-col gap-4 p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-2">
                        <h3 className="font-serif text-xl font-semibold">{project.name}</h3>
                        <div className="flex flex-wrap gap-2">
                          <StatusBadge status={project.status} />
                          {project.deleted_at ? (
                            <StatusBadge status="archived" label="回收站" />
                          ) : null}
                        </div>
                      </div>
                      <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-secondary)]">
                        {project.genre ?? "未设题材"}
                      </p>
                    </div>

                    <dl className="grid gap-2 text-sm text-[var(--text-secondary)]">
                      <div className="flex justify-between gap-4">
                        <dt>目标字数</dt>
                        <dd>{project.target_words ?? "未设置"}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt>系统凭证池</dt>
                        <dd>{project.allow_system_credential_pool ? "开启" : "关闭"}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt>模板</dt>
                        <dd>
                          {project.template_id
                            ? (templateNameById.get(project.template_id) ?? "模板未同步")
                            : "基础项目"}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt>更新时间</dt>
                        <dd>{new Date(project.updated_at).toLocaleString("zh-CN")}</dd>
                      </div>
                    </dl>

                    <div className="flex flex-wrap gap-2">
                      {!project.deleted_at ? (
                        <>
                          <Link
                            className="ink-button"
                            href={`/workspace/project/${project.id}/studio?panel=setting`}
                          >
                            进入 Studio
                          </Link>
                          <Link
                            className="ink-button-secondary"
                            href={`/workspace/project/${project.id}/engine`}
                          >
                            打开 Engine
                          </Link>
                          <button
                            className="ink-button-danger"
                            disabled={actionMutation.isPending}
                            onClick={() =>
                              actionMutation.mutate({ type: "delete", projectId: project.id })
                            }
                          >
                            移入回收站
                          </button>
                        </>
                      ) : (
                        <button
                          className="ink-button"
                          disabled={actionMutation.isPending}
                          onClick={() =>
                            actionMutation.mutate({ type: "restore", projectId: project.id })
                          }
                        >
                          恢复项目
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </SectionCard>

      {showSettings ? <CredentialCenter /> : null}
    </div>
  );
}
