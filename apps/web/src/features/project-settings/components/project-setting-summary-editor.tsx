"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { AppSelect } from "@/components/ui/app-select";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  pickIncubatorCredentialOption,
} from "@/features/shared/assistant/assistant-credential-support";
import {
  buildProjectSettingSummarySourceExcerpt,
  buildProjectSettingSummaryProviderOptions,
  buildProjectSettingSummarySaveFeedback,
  invalidateProjectSettingSummaryQueries,
  loadProjectSettingSummaryEditorResources,
  normalizeProjectSettingSummarySourceContent,
  PROJECT_SETTING_SUMMARY_SOURCE_DOCUMENT_PATH,
  resolveProjectSettingSummaryPreferredModelName,
  resolveProjectSettingSummaryPreferredProvider,
} from "@/features/project-settings/components/project-setting-summary-editor-support";
import { ProjectSettingSummaryPreview } from "@/features/project-settings/components/project-setting-summary-preview";
import { getErrorMessage } from "@/lib/api/client";
import {
  buildIncubatorConversationDraft,
  getProjectDocument,
  updateProjectSetting,
} from "@/lib/api/projects";
import type {
  ProjectDetail,
  ProjectIncubatorConversationDraft,
  ProjectSetting,
  ProjectSettingSnapshot,
} from "@/lib/api/types";

type ProjectSettingSummaryEditorProps = {
  initialSetting: ProjectSetting | null;
  onCancel: () => void;
  onDirtyChange?: (isDirty: boolean) => void;
  onSaved: (
    snapshot: ProjectSettingSnapshot,
    draft: ProjectIncubatorConversationDraft,
  ) => void;
  projectId: string;
};

const SETTINGS_LINK_CLASS =
  "inline-flex items-center text-sm text-accent-primary underline decoration-accent-primary/25 underline-offset-4 hover:text-text-primary";

export function ProjectSettingSummaryEditor({
  initialSetting,
  onCancel,
  onDirtyChange,
  onSaved,
  projectId,
}: Readonly<ProjectSettingSummaryEditorProps>) {
  const queryClient = useQueryClient();
  const [modelName, setModelName] = useState("");
  const [preview, setPreview] = useState<ProjectIncubatorConversationDraft | null>(null);
  const [provider, setProvider] = useState("");

  const resourcesQuery = useQuery({
    queryKey: ["project-setting-summary-editor-resources", projectId],
    queryFn: () => loadProjectSettingSummaryEditorResources(projectId),
  });
  const sourceDocumentQuery = useQuery({
    queryKey: ["project-setting-summary-source-document", projectId],
    queryFn: () => getProjectDocument(projectId, PROJECT_SETTING_SUMMARY_SOURCE_DOCUMENT_PATH),
  });
  const credentialOptions = useMemo(
    () => resourcesQuery.data?.credentialOptions ?? [],
    [resourcesQuery.data?.credentialOptions],
  );
  const preferredProvider = resolveProjectSettingSummaryPreferredProvider(resourcesQuery.data);
  const selectedOption = useMemo(
    () => pickIncubatorCredentialOption(credentialOptions, provider || preferredProvider),
    [credentialOptions, preferredProvider, provider],
  );
  const providerOptions = useMemo(
    () => buildProjectSettingSummaryProviderOptions(credentialOptions),
    [credentialOptions],
  );
  const preferredModelName = useMemo(
    () =>
      resolveProjectSettingSummaryPreferredModelName(
        resourcesQuery.data,
        selectedOption?.provider ?? "",
      ),
    [resourcesQuery.data, selectedOption?.provider],
  );
  const resolvedProvider = provider.trim() || selectedOption?.provider || "";
  const resolvedModelName = modelName.trim() || preferredModelName || selectedOption?.defaultModel || "";
  const sourceContent = normalizeProjectSettingSummarySourceContent(
    sourceDocumentQuery.data?.content,
  );
  const sourceExcerpt = buildProjectSettingSummarySourceExcerpt(
    sourceDocumentQuery.data?.content,
  );
  const sourceCharacterCount = sourceContent.length;
  const studioDocumentHref = `/workspace/project/${projectId}/studio?${new URLSearchParams({
    doc: PROJECT_SETTING_SUMMARY_SOURCE_DOCUMENT_PATH,
    panel: "overview",
  }).toString()}`;
  const isDirty = preview !== null;
  const hasAvailableProvider = providerOptions.length > 0;
  const hasSourceContent = sourceContent.length > 0;

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  const draftMutation = useMutation({
    mutationFn: async () => {
      if (!resolvedProvider) {
        throw new Error("请先选择一个可用模型连接。");
      }
      const sourceDocument = await getProjectDocument(
        projectId,
        PROJECT_SETTING_SUMMARY_SOURCE_DOCUMENT_PATH,
      );
      queryClient.setQueryData(
        ["project-setting-summary-source-document", projectId],
        sourceDocument,
      );
      const latestSourceContent = normalizeProjectSettingSummarySourceContent(
        sourceDocument.content,
      );
      if (!latestSourceContent) {
        throw new Error("项目说明还是空的，请先补充内容。");
      }
      return buildIncubatorConversationDraft({
        conversation_text: latestSourceContent,
        base_project_setting: initialSetting ?? undefined,
        model_name: resolvedModelName || undefined,
        provider: resolvedProvider,
      });
    },
    onSuccess: (draft) => {
      setPreview(draft);
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "提炼摘要失败",
        tone: "danger",
      }),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!preview) {
        throw new Error("请先提炼一版摘要，再决定是否保存。");
      }
      return updateProjectSetting(projectId, preview.project_setting);
    },
    onSuccess: (snapshot) => {
      if (!preview) {
        return;
      }
      queryClient.setQueryData(["project", projectId], (current: ProjectDetail | undefined) =>
        current
          ? {
              ...current,
              genre: snapshot.genre,
              project_setting: snapshot.project_setting,
              target_words: snapshot.target_words,
            }
          : current,
      );
      invalidateProjectSettingSummaryQueries(queryClient, projectId, snapshot.impact);
      showAppNotice({
        content: buildProjectSettingSummarySaveFeedback(snapshot.impact),
        title: "项目摘要",
        tone: "success",
      });
      onSaved(snapshot, preview);
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "保存摘要失败",
        tone: "danger",
      }),
  });

  const handleCancel = () => {
    if (isDirty && !window.confirm("当前还有未保存的摘要草稿，关闭后会丢失。是否继续？")) {
      return;
    }
    onCancel();
  };

  return (
    <section className="space-y-4 rounded-3xl border border-accent-primary-muted bg-glass p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-xs uppercase tracking-[0.18em] text-accent-primary">更新摘要</p>
          <h3 className="font-serif text-lg font-semibold text-text-primary">直接从项目说明提取结构化摘要</h3>
          <p className="text-sm leading-6 text-text-secondary">
            这里会读取最新的项目说明内容交给 AI 提炼，不需要再手动复制人物、世界观、剧情走向和约束要求。
          </p>
        </div>
        <StatusBadge status={preview?.setting_completeness.status ?? "draft"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <div className="space-y-3">
          <section className="space-y-3 rounded-2xl bg-muted shadow-sm p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-sm font-medium text-text-primary">提取来源</p>
                <p className="text-sm leading-6 text-text-secondary">
                  每次提取都会直接读取 <span className="font-medium text-text-primary">项目说明.md</span> 的最新内容。
                </p>
              </div>
              <Link className={SETTINGS_LINK_CLASS} href={studioDocumentHref}>
                前往编辑项目说明
              </Link>
            </div>
            {sourceDocumentQuery.isLoading ? (
              <p className="text-sm text-text-secondary">正在读取项目说明...</p>
            ) : sourceDocumentQuery.error ? (
              <p className="text-sm leading-6 text-accent-danger">
                {getErrorMessage(sourceDocumentQuery.error)}
              </p>
            ) : hasSourceContent ? (
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.16em] text-text-secondary">
                  {PROJECT_SETTING_SUMMARY_SOURCE_DOCUMENT_PATH} · {sourceCharacterCount} 字
                </p>
                <div className="rounded-2xl bg-surface shadow-sm px-4 py-3">
                  <p className="break-words text-sm leading-7 text-text-primary">
                    {sourceExcerpt}
                  </p>
                </div>
              </div>
            ) : (
              <div className="callout-warning px-4 py-3 text-sm leading-6 text-accent-warning">
                项目说明还是空的。先去文稿里写清楚故事背景、人物关系和约束，再回来提取摘要。
              </div>
            )}
          </section>
          <div className="grid gap-3 md:grid-cols-[minmax(0,220px)_minmax(0,1fr)]">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-primary">模型连接</span>
              <AppSelect
                ariaLabel="摘要提炼连接"
                density="roomy"
                disabled={!hasAvailableProvider || resourcesQuery.isLoading}
                options={providerOptions}
                placeholder="选择连接"
                value={resolvedProvider}
                onChange={(value) => {
                  setProvider(value);
                  setModelName("");
                  setPreview(null);
                }}
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-primary">模型名（可选）</span>
              <input
                className="ink-input min-h-[2.9rem] rounded-2xl"
                placeholder={selectedOption?.defaultModel || "留空则使用连接默认模型"}
                value={resolvedModelName}
                onChange={(event) => {
                  setModelName(event.target.value);
                  setPreview(null);
                }}
              />
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              className="ink-button"
              disabled={
                !hasSourceContent
                || draftMutation.isPending
                || !hasAvailableProvider
                || sourceDocumentQuery.isLoading
              }
              type="button"
              onClick={() => draftMutation.mutate()}
            >
              {draftMutation.isPending ? "提取中..." : "从项目说明提取"}
            </button>
            <button
              className="ink-button-secondary"
              disabled={!preview || saveMutation.isPending}
              type="button"
              onClick={() => saveMutation.mutate()}
            >
              {saveMutation.isPending ? "保存中..." : "保存摘要"}
            </button>
            <button className="ink-button-secondary" type="button" onClick={handleCancel}>
              取消
            </button>
          </div>
        </div>

        <aside className="space-y-3 rounded-2xl bg-muted shadow-sm p-4">
          {resourcesQuery.isLoading ? (
            <p className="text-sm text-text-secondary">正在读取项目偏好和模型连接...</p>
          ) : resourcesQuery.error ? (
            <p className="text-sm leading-6 text-accent-danger">{getErrorMessage(resourcesQuery.error)}</p>
          ) : hasAvailableProvider ? (
            <>
              <p className="text-sm font-medium text-text-primary">当前默认连接</p>
              <p className="text-sm leading-6 text-text-secondary">
                {selectedOption ? `${selectedOption.provider} · ${selectedOption.displayLabel}` : "将按可用连接自动回退。"}
              </p>
              <p className="text-sm leading-6 text-text-secondary">
                提取时会自动读取最新项目说明，不需要再手动整理一份自由描述。
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium text-text-primary">还没有可用连接</p>
              <div className="space-y-2 text-sm leading-6 text-text-secondary">
                <p>先去启用项目或全局模型连接，再回来提取项目说明里的摘要。</p>
                <Link
                  className={SETTINGS_LINK_CLASS}
                  href={`/workspace/lobby/settings?tab=credentials&scope=project&project=${projectId}&sub=list`}
                >
                  打开模型连接
                </Link>
              </div>
            </>
          )}
        </aside>
      </div>

      {preview ? <ProjectSettingSummaryPreview draft={preview} /> : null}
    </section>
  );
}
