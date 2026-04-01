"use client";

import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";

import { AppSelect } from "@/components/ui/app-select";
import type { AssistantPreferences } from "@/lib/api/types";

import {
  isAssistantPreferencesDirty,
  normalizeAssistantMaxOutputTokenDraft,
  toAssistantPreferencesDraft,
  type AssistantPreferencesDraft,
  type AssistantProviderOption,
} from "./assistant-preferences-support";

type AssistantPreferencesFormProps = {
  emptyStateText: string;
  formDescription: string;
  inheritedPreferences?: AssistantPreferences;
  isPending: boolean;
  onDirtyChange?: (isDirty: boolean) => void;
  onSubmit: (draft: AssistantPreferencesDraft) => void;
  placeholderText: string;
  preferences: AssistantPreferences;
  providerOptions: AssistantProviderOption[];
  showCredentialEmptyState: boolean;
};

export function AssistantPreferencesForm({
  emptyStateText,
  formDescription,
  inheritedPreferences,
  isPending,
  onDirtyChange,
  onSubmit,
  placeholderText,
  preferences,
  providerOptions,
  showCredentialEmptyState,
}: Readonly<AssistantPreferencesFormProps>) {
  const [draft, setDraft] = useState<AssistantPreferencesDraft>(() => toAssistantPreferencesDraft(preferences));
  const isDirty = isAssistantPreferencesDirty(draft, preferences);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form
      className="panel-muted space-y-10 p-10"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft);
      }}
    >
      <div className="rounded-2xl bg-[rgba(248,243,235,0.92)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
          {formDescription}
        </div>
      <div className="grid gap-4 xl:grid-cols-[repeat(3,minmax(0,1fr))]">
        <AssistantProviderField draft={draft} providerOptions={providerOptions} setDraft={setDraft} />
        <AssistantModelField
          draft={draft}
          inheritedModelName={inheritedPreferences?.default_model_name ?? undefined}
          setDraft={setDraft}
        />
        <AssistantMaxOutputTokensField
          draft={draft}
          inheritedMaxOutputTokens={inheritedPreferences?.default_max_output_tokens ?? undefined}
          placeholderText={placeholderText}
          setDraft={setDraft}
        />
      </div>
      {showCredentialEmptyState ? (
        <div className="rounded-2xl bg-[rgba(183,121,31,0.08)] px-4 py-3 text-sm text-[var(--accent-warning)]">
          {emptyStateText}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button className="ink-button" disabled={isPending || !isDirty} type="submit">
          {isPending ? "保存中..." : "保存设置"}
        </button>
        <button
          className="ink-button-secondary"
          disabled={isPending || !isDirty}
          onClick={() => setDraft(toAssistantPreferencesDraft(preferences))}
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
  providerOptions: AssistantProviderOption[];
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
        建议直接从可用连接里选择，不需要自己记任何渠道标识。
      </p>
    </div>
  );
}

function AssistantModelField({
  draft,
  inheritedModelName,
  setDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  inheritedModelName?: string;
  setDraft: Dispatch<SetStateAction<AssistantPreferencesDraft>>;
}>) {
  const placeholder = inheritedModelName
    ? `当前继承：${inheritedModelName}`
    : "例如：gpt-4.1-mini";

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
        placeholder={placeholder}
        value={draft.defaultModelName}
      />
      <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
        通常留空即可。只有你想固定某个模型时，再单独填写。
      </p>
    </div>
  );
}

function AssistantMaxOutputTokensField({
  draft,
  inheritedMaxOutputTokens,
  placeholderText,
  setDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  inheritedMaxOutputTokens?: number;
  placeholderText: string;
  setDraft: Dispatch<SetStateAction<AssistantPreferencesDraft>>;
}>) {
  const placeholder = inheritedMaxOutputTokens
    ? `当前继承：${inheritedMaxOutputTokens}`
    : placeholderText;

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
        placeholder={placeholder}
        value={draft.defaultMaxOutputTokens}
      />
      <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
        只控制单次回复长度，不影响模型本身的输入容量。留空会回到当前作用域的默认值。
      </p>
    </div>
  );
}
