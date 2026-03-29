"use client";

import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { AppSelect } from "@/components/ui/app-select";
import { SectionCard } from "@/components/ui/section-card";
import {
  getMyAssistantPreferences,
  updateMyAssistantPreferences,
} from "@/lib/api/assistant";
import { listCredentials } from "@/lib/api/credential";
import { getErrorMessage } from "@/lib/api/client";

import {
  buildAssistantPreferencesPayload,
  buildAssistantProviderOptions,
  isAssistantPreferencesDirty,
  normalizeAssistantMaxOutputTokenDraft,
  toAssistantPreferencesDraft,
  type AssistantPreferencesDraft,
} from "./assistant-preferences-support";

type AssistantPreferencesPanelProps = {
  headerAction?: React.ReactNode;
  onDirtyChange?: (isDirty: boolean) => void;
};

export function AssistantPreferencesPanel({
  headerAction,
  onDirtyChange,
}: AssistantPreferencesPanelProps) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const preferencesQuery = useQuery({
    queryKey: ["assistant-preferences", "me"],
    queryFn: getMyAssistantPreferences,
  });
  const credentialsQuery = useQuery({
    queryKey: ["credentials", "user", "assistant-preferences"],
    queryFn: () => listCredentials("user"),
  });
  const mutation = useMutation({
    mutationFn: (nextDraft: AssistantPreferencesDraft) =>
      updateMyAssistantPreferences(buildAssistantPreferencesPayload(nextDraft)),
    onSuccess: async () => {
      const message = "AI 偏好已保存。";
      setFeedback(message);
      showAppNotice({
        content: message,
        title: "AI 偏好",
        tone: "success",
      });
      await queryClient.invalidateQueries({ queryKey: ["assistant-preferences", "me"] });
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      setFeedback(message);
      showAppNotice({
        content: message,
        tone: "danger",
      });
    },
  });
  const formKey = useMemo(
    () => buildAssistantPreferencesFormKey(preferencesQuery.data),
    [preferencesQuery.data],
  );
  const providerOptions = useMemo(
    () => buildAssistantProviderOptions(credentialsQuery.data),
    [credentialsQuery.data],
  );
  const hasAvailableProvider = providerOptions.length > 1;
  const showCredentialEmptyState = !credentialsQuery.isLoading && !hasAvailableProvider;

  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);

  return (
    <SectionCard
      action={headerAction}
      description="新聊天会优先使用默认连接和模型，临时切换只影响当前对话。"
      title="AI 偏好"
    >
      <div className="space-y-4">
        {preferencesQuery.isLoading && !preferencesQuery.data ? (
          <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载 AI 偏好...</div>
        ) : null}
        {preferencesQuery.error ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
            {getErrorMessage(preferencesQuery.error)}
          </div>
        ) : null}
        {preferencesQuery.data ? (
          <AssistantPreferencesForm
            key={formKey}
            isPending={mutation.isPending}
            preferences={preferencesQuery.data}
            providerOptions={providerOptions}
            showCredentialEmptyState={showCredentialEmptyState}
            onDirtyChange={onDirtyChange}
            onResetFeedback={() => setFeedback(null)}
            onSubmit={(draft) => {
              setFeedback(null);
              mutation.mutate(draft);
            }}
          />
        ) : null}
      </div>
    </SectionCard>
  );
}

function AssistantPreferencesForm({
  isPending,
  onResetFeedback,
  onSubmit,
  preferences,
  providerOptions,
  showCredentialEmptyState,
  onDirtyChange,
}: Readonly<{
  isPending: boolean;
  onDirtyChange?: (isDirty: boolean) => void;
  onResetFeedback: () => void;
  onSubmit: (draft: AssistantPreferencesDraft) => void;
  preferences: Awaited<ReturnType<typeof getMyAssistantPreferences>>;
  providerOptions: ReturnType<typeof buildAssistantProviderOptions>;
  showCredentialEmptyState: boolean;
}>) {
  const [draft, setDraft] = useState<AssistantPreferencesDraft>(() => toAssistantPreferencesDraft(preferences));
  const isDirty = isAssistantPreferencesDirty(draft, preferences);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form
      className="panel-muted space-y-4 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft);
      }}
    >
      <div className="rounded-2xl bg-[rgba(58,124,165,0.06)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        保存当前账号的新聊天默认值。这里只控制默认连接、默认模型和单次回复上限；输入容量仍由模型本身决定。
      </div>
      <div className="grid gap-4 xl:grid-cols-[repeat(3,minmax(0,1fr))]">
        <AssistantProviderField draft={draft} providerOptions={providerOptions} setDraft={setDraft} />
        <AssistantModelField draft={draft} setDraft={setDraft} />
        <AssistantMaxOutputTokensField draft={draft} setDraft={setDraft} />
      </div>
      {showCredentialEmptyState ? (
        <div className="rounded-2xl bg-[rgba(183,121,31,0.08)] px-4 py-3 text-sm text-[var(--accent-warning)]">
          你还没有启用可用连接。可以先去“模型连接”页添加或启用，再回来设置默认聊天方式。
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button className="ink-button" disabled={isPending || !isDirty} type="submit">
          {isPending ? "保存中..." : "保存设置"}
        </button>
        <button
          className="ink-button-secondary"
          disabled={isPending || !isDirty}
          onClick={() => {
            onResetFeedback();
            setDraft(toAssistantPreferencesDraft(preferences));
          }}
          type="button"
        >
          还原
        </button>
      </div>
    </form>
  );
}

function AssistantProviderField({
  draft,
  providerOptions,
  setDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  providerOptions: ReturnType<typeof buildAssistantProviderOptions>;
  setDraft: Dispatch<SetStateAction<AssistantPreferencesDraft>>;
}>) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="assistant-default-provider">
        默认连接
      </label>
      <AppSelect
        className="min-w-0"
        emptyText="暂无可用连接"
        id="assistant-default-provider"
        options={providerOptions}
        value={draft.defaultProvider}
        onChange={(value) =>
          setDraft((current) => ({
            ...current,
            defaultProvider: value,
          }))
        }
      />
      <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
        建议直接从已启用的连接里选，不需要自己记连接标识。
      </p>
    </div>
  );
}

function AssistantModelField({
  draft,
  setDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  setDraft: Dispatch<SetStateAction<AssistantPreferencesDraft>>;
}>) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="assistant-default-model-name">
        默认模型
      </label>
      <input
        className="ink-input"
        id="assistant-default-model-name"
        onChange={(event) =>
          setDraft((current) => ({
            ...current,
            defaultModelName: event.target.value,
          }))
        }
        placeholder="例如：gpt-4o-mini"
        value={draft.defaultModelName}
      />
      <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
        通常留空即可，系统会使用该连接自己的默认模型。只有你想固定某个模型时再填写。
      </p>
    </div>
  );
}

function AssistantMaxOutputTokensField({
  draft,
  setDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  setDraft: Dispatch<SetStateAction<AssistantPreferencesDraft>>;
}>) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="assistant-default-max-output-tokens">
        默认单次回复上限
      </label>
      <input
        className="ink-input"
        id="assistant-default-max-output-tokens"
        inputMode="numeric"
        min={128}
        onChange={(event) =>
          setDraft((current) => ({
            ...current,
            defaultMaxOutputTokens: normalizeAssistantMaxOutputTokenDraft(event.target.value),
          }))
        }
        placeholder="4096"
        value={draft.defaultMaxOutputTokens}
      />
      <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
        默认值是 4096。想让长回答更完整时再调高，留空会恢复到系统默认值。
      </p>
    </div>
  );
}

function buildAssistantPreferencesFormKey(
  preferences: Awaited<ReturnType<typeof getMyAssistantPreferences>> | undefined,
) {
  if (!preferences) {
    return "assistant-preferences:empty";
  }
  return [
    preferences.default_provider ?? "none",
    preferences.default_model_name ?? "none",
    String(preferences.default_max_output_tokens),
  ].join(":");
}
