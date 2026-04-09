"use client";

import { useEffect, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { SectionCard } from "@/components/ui/section-card";
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
  headerAction,
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
      const message = scope === "project" ? "项目 AI 偏好已保存。" : "AI 偏好已保存。";
      showAppNotice({
        content: message,
        title: copy.title,
        tone: "success",
      });
      await queryClient.invalidateQueries({
        queryKey: buildAssistantPreferencesQueryKey(scope, projectId),
      });
    },
    onError: (error) => {
      showAppNotice({
        content: getErrorMessage(error),
        tone: "danger",
      });
    },
  });
  const formKey = useMemo(
    () => buildAssistantPreferencesFormKey(preferencesQuery.data),
    [preferencesQuery.data],
  );
  const providerOptions = useMemo(
    () => buildAssistantProviderOptions(credentialsQuery.data, scope),
    [credentialsQuery.data, scope],
  );
  const hasAvailableProvider = providerOptions.some((item) => item.value !== "");
  const showCredentialEmptyState = !credentialsQuery.isLoading && !hasAvailableProvider;

  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);

  return (
    <SectionCard
      action={headerAction}
      description={copy.cardDescription}
      title={copy.title}
    >
      <div className="space-y-4">
        {preferencesQuery.isLoading && !preferencesQuery.data ? (
          <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{copy.loadingText}</div>
        ) : null}
        {preferencesQuery.error ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
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
    </SectionCard>
  );
}

function buildAssistantPreferencesCopy(scope: AssistantPreferencesScope) {
  if (scope === "project") {
    return {
      cardDescription: "只影响当前项目里的聊天默认方式；留空时继续跟随个人 AI 偏好。",
      emptyStateText: "当前项目和个人账号里都还没有可用连接。可以先去“模型连接”页添加或启用。",
      formDescription: "项目层会覆盖这个项目默认使用的连接、模型、回复上限和官方思考参数，不会改动你的个人聊天习惯。",
      loadingText: "正在加载项目 AI 偏好...",
      maxOutputPlaceholder: "留空则跟随个人设置",
      title: "项目 AI 偏好",
    };
  }
  return {
    cardDescription: "新聊天会优先使用默认连接和模型，临时切换只影响当前对话。",
    emptyStateText: "你还没有启用可用连接。可以先去“模型连接”页添加或启用，再回来设置默认聊天方式。",
    formDescription: "保存当前账号的新聊天默认值。这里会同时记录默认连接、模型、回复上限和官方思考参数；输入容量仍由模型本身决定。",
    loadingText: "正在加载 AI 偏好...",
    maxOutputPlaceholder: "4096",
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
    const resolvedProjectId = requireProjectId(projectId);
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
    return getProjectAssistantPreferences(requireProjectId(projectId));
  }
  return getMyAssistantPreferences();
}

function saveAssistantPreferences(
  scope: AssistantPreferencesScope,
  projectId: string | undefined,
  payload: AssistantPreferencesUpdatePayload,
) {
  if (scope === "project") {
    return updateProjectAssistantPreferences(requireProjectId(projectId), payload);
  }
  return updateMyAssistantPreferences(payload);
}

function requireProjectId(projectId: string | undefined) {
  if (projectId) {
    return projectId;
  }
  throw new Error("缺少项目 ID，无法读取项目 AI 偏好。");
}
