"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { AppSelect } from "@/components/ui/app-select";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  pickIncubatorCredentialOption,
} from "@/features/lobby/components/incubator-chat-credential-support";
import {
  buildProjectSettingConversationSeed,
} from "@/features/project/components/project-setting-summary-support";
import {
  buildProjectSettingSummaryProviderOptions,
  buildProjectSettingSummarySaveFeedback,
  invalidateProjectSettingSummaryQueries,
  loadProjectSettingSummaryEditorResources,
  resolveProjectSettingSummaryPreferredModelName,
  resolveProjectSettingSummaryPreferredProvider,
} from "@/features/project-settings/components/project-setting-summary-editor-support";
import { ProjectSettingSummaryPreview } from "@/features/project-settings/components/project-setting-summary-preview";
import { getErrorMessage } from "@/lib/api/client";
import {
  buildIncubatorConversationDraft,
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
  "inline-flex items-center text-sm text-[var(--accent-primary)] underline decoration-[rgba(90,122,107,0.28)] underline-offset-4 hover:text-[var(--text-primary)]";

export function ProjectSettingSummaryEditor({
  initialSetting,
  onCancel,
  onDirtyChange,
  onSaved,
  projectId,
}: Readonly<ProjectSettingSummaryEditorProps>) {
  const queryClient = useQueryClient();
  const initialConversationText = useMemo(
    () => buildProjectSettingConversationSeed(initialSetting),
    [initialSetting],
  );
  const [conversationText, setConversationText] = useState(initialConversationText);
  const [modelName, setModelName] = useState("");
  const [preview, setPreview] = useState<ProjectIncubatorConversationDraft | null>(null);
  const [provider, setProvider] = useState("");

  const resourcesQuery = useQuery({
    queryKey: ["project-setting-summary-editor-resources", projectId],
    queryFn: () => loadProjectSettingSummaryEditorResources(projectId),
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
  const isDirty = preview !== null || conversationText.trim() !== initialConversationText.trim();
  const hasAvailableProvider = providerOptions.length > 0;

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  const draftMutation = useMutation({
    mutationFn: async () => {
      if (!resolvedProvider) {
        throw new Error("请先选择一个可用模型连接。");
      }
      return buildIncubatorConversationDraft({
        conversation_text: conversationText,
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
      queryClient.setQueryData(["setting-check", projectId], preview.setting_completeness);
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
    <section className="space-y-4 rounded-[24px] border border-[rgba(90,122,107,0.12)] bg-[rgba(255,255,255,0.82)] p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-primary)]">更新摘要</p>
          <h3 className="font-serif text-lg font-semibold text-[var(--text-primary)]">用自然语言写，交给 AI 提炼结构化摘要</h3>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            这里适合写人物、世界观、剧情走向和约束要求。保存后，当前已确认的大纲、开篇和章节会按实际影响标记为 stale，方便重新核对。
          </p>
        </div>
        <StatusBadge status={preview?.setting_completeness.status ?? "draft"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <div className="space-y-3">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-[var(--text-primary)]">自由描述</span>
            <textarea
              className="min-h-[240px] w-full rounded-[18px] border border-[var(--line-soft)] bg-[var(--bg-surface)] px-4 py-3 text-sm leading-7 text-[var(--text-primary)] shadow-sm outline-none transition focus:border-[rgba(90,122,107,0.38)] focus:ring-2 focus:ring-[rgba(90,122,107,0.12)]"
              placeholder="例如：这是一部发生在旧城区更新期的都市治愈小说。主角是守着祖传书店的年轻店主……"
              value={conversationText}
              onChange={(event) => {
                setConversationText(event.target.value);
                setPreview(null);
              }}
            />
          </label>
          <div className="grid gap-3 md:grid-cols-[minmax(0,220px)_minmax(0,1fr)]">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--text-primary)]">模型连接</span>
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
              <span className="text-sm font-medium text-[var(--text-primary)]">模型名（可选）</span>
              <input
                className="ink-input min-h-[2.9rem] rounded-[16px]"
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
              disabled={!conversationText.trim() || draftMutation.isPending || !hasAvailableProvider}
              type="button"
              onClick={() => draftMutation.mutate()}
            >
              {draftMutation.isPending ? "提炼中..." : "AI 提炼摘要"}
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

        <aside className="space-y-3 rounded-[20px] border border-[var(--line-soft)] bg-[rgba(248,243,235,0.62)] p-4">
          {resourcesQuery.isLoading ? (
            <p className="text-sm text-[var(--text-secondary)]">正在读取项目偏好和模型连接...</p>
          ) : resourcesQuery.error ? (
            <p className="text-sm leading-6 text-[var(--accent-danger)]">{getErrorMessage(resourcesQuery.error)}</p>
          ) : hasAvailableProvider ? (
            <>
              <p className="text-sm font-medium text-[var(--text-primary)]">当前默认连接</p>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
                {selectedOption ? `${selectedOption.provider} · ${selectedOption.displayLabel}` : "将按可用连接自动回退。"}
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium text-[var(--text-primary)]">还没有可用连接</p>
              <div className="space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
                <p>先去启用项目或全局模型连接，再回来让 AI 提炼摘要。</p>
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
