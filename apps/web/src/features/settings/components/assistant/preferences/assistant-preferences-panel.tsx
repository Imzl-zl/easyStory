"use client";

import { useEffect, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import {
  getMyAssistantPreferences,
  getProjectAssistantPreferences,
  updateProjectAssistantPreferences,
  updateMyAssistantPreferences,
} from "@/lib/api/assistant";
import { listCredentials } from "@/lib/api/credential";
import type { AssistantPreferences, AssistantPreferencesUpdatePayload, CredentialView } from "@/lib/api/types";
import { getErrorMessage } from "@/lib/api/client";

import {
  buildAssistantPreferencesFormKey,
  buildAssistantProviderOptions,
  type AssistantPreferencesScope,
} from "@/features/settings/components/assistant/preferences/assistant-preferences-support";
import { AssistantPreferencesForm } from "@/features/settings/components/assistant/preferences/assistant-preferences-form";

type AssistantPreferencesPanelProps = {
  headerAction?: React.ReactNode;
  onDirtyChange?: (isDirty: boolean) => void;
  projectId?: string;
  scope?: AssistantPreferencesScope;
};

export function AssistantPreferencesPanel({
  onDirtyChange,
  projectId,
  scope = "user",
}: AssistantPreferencesPanelProps) {
  const queryClient = useQueryClient();
  const preferencesQuery = useQuery({
    queryKey: buildAssistantPreferencesQueryKey(scope, projectId),
    queryFn: () => loadAssistantPreferences(scope, projectId),
  });
  const userPreferencesQuery = useQuery({
    queryKey: ["assistant-preferences", "user", "me"] as const,
    queryFn: () => getMyAssistantPreferences(),
    enabled: scope === "project",
  });
  const credentialsQuery = useQuery({
    queryKey: ["credentials", scope, projectId ?? "none", "assistant-preferences"],
    queryFn: () => loadAssistantPreferenceCredentials(scope, projectId),
  });
  const copy = buildAssistantPreferencesCopy(scope);
  const mutation = useMutation({
    mutationFn: (payload: AssistantPreferencesUpdatePayload) =>
      saveAssistantPreferences(scope, projectId, payload),
    onSuccess: async () => {
      showAppNotice({ content: scope === "project" ? "项目 AI 偏好已保存。" : "AI 偏好已保存。", title: copy.title, tone: "success" });
      await queryClient.invalidateQueries({ queryKey: buildAssistantPreferencesQueryKey(scope, projectId) });
    },
    onError: (error) => showAppNotice({ content: getErrorMessage(error), tone: "danger" }),
  });
  const formKey = useMemo(() => buildAssistantPreferencesFormKey(preferencesQuery.data), [preferencesQuery.data]);
  const providerOptions = useMemo(() => buildAssistantProviderOptions(credentialsQuery.data, scope), [credentialsQuery.data, scope]);
  const hasAvailableProvider = providerOptions.some((item) => item.value !== "");
  const showCredentialEmptyState = !credentialsQuery.isLoading && !hasAvailableProvider;

  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);

  return (
    <section
      className="rounded-lg"
      style={{
        background: "var(--bg-canvas)",
        border: "1px solid var(--line-soft)",
      }}
    >
      {/* Section Header */}
      <div className="px-4 pt-4 pb-3" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <h2 className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
          {copy.title}
        </h2>
        <p className="mt-0.5 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          {copy.cardDescription}
        </p>
      </div>

      {/* Form */}
      <div className="px-4 py-4">
        {preferencesQuery.isLoading && !preferencesQuery.data ? (
          <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>{copy.loadingText}</p>
        ) : null}
        {preferencesQuery.error ? (
          <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {getErrorMessage(preferencesQuery.error)}
          </div>
        ) : null}
        {preferencesQuery.data ? (
          <AssistantPreferencesForm
            key={formKey}
            emptyStateText={copy.emptyStateText}
            formDescription={copy.formDescription}
            inheritedPreferences={scope === "project" ? userPreferencesQuery.data : undefined}
            isPending={mutation.isPending}
            preferences={preferencesQuery.data}
            placeholderText={copy.maxOutputPlaceholder}
            providerOptions={providerOptions}
            showCredentialEmptyState={showCredentialEmptyState}
            onDirtyChange={onDirtyChange}
            onSubmit={(payload) => mutation.mutate(payload)}
          />
        ) : null}
      </div>
    </section>
  );
}

function buildAssistantPreferencesCopy(scope: AssistantPreferencesScope) {
  if (scope === "project") {
    return {
      cardDescription: "只影响当前项目里的聊天默认方式；留空时继续跟随个人 AI 偏好。",
      emptyStateText: "当前项目和个人账号里都还没有可用连接。可以先去「模型连接」页添加或启用。",
      formDescription: "覆盖此项目的默认设置。",
      loadingText: "正在加载项目 AI 偏好...",
      maxOutputPlaceholder: "留空则跟随个人设置",
      title: "项目 AI 偏好",
    };
  }
  return {
    cardDescription: "新聊天会优先使用默认连接和模型，临时切换只影响当前对话。",
    emptyStateText: "你还没有启用可用连接。可以先去「模型连接」页添加或启用，再回来设置默认聊天方式。",
    formDescription: "新聊天的默认设置。",
    loadingText: "正在加载 AI 偏好...",
    maxOutputPlaceholder: "留空则不单独指定",
    title: "AI 偏好",
  };
}

function buildAssistantPreferencesQueryKey(scope: AssistantPreferencesScope, projectId?: string) {
  return ["assistant-preferences", scope, projectId ?? "me"] as const;
}

async function loadAssistantPreferenceCredentials(
  scope: AssistantPreferencesScope,
  projectId?: string,
): Promise<CredentialView[]> {
  if (scope === "project") {
    const resolvedProjectId = projectId ?? "";
    const [projectCredentials, userCredentials] = await Promise.all([
      listCredentials("project", resolvedProjectId),
      listCredentials("user"),
    ]);
    return [...projectCredentials, ...userCredentials];
  }
  return listCredentials("user");
}

function loadAssistantPreferences(
  scope: AssistantPreferencesScope,
  projectId?: string,
): Promise<AssistantPreferences> {
  if (scope === "project") {
    return getProjectAssistantPreferences(projectId ?? "");
  }
  return getMyAssistantPreferences();
}

function saveAssistantPreferences(
  scope: AssistantPreferencesScope,
  projectId: string | undefined,
  payload: AssistantPreferencesUpdatePayload,
) {
  if (scope === "project") {
    return updateProjectAssistantPreferences(projectId ?? "", payload);
  }
  return updateMyAssistantPreferences(payload);
}
