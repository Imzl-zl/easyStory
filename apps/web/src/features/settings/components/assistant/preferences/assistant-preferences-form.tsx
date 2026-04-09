"use client";

import { useEffect, useState } from "react";

import { AppSelect } from "@/components/ui/app-select";
import type { AssistantPreferences, AssistantPreferencesUpdatePayload } from "@/lib/api/types";
import {
  buildAssistantReasoningShapeError,
  normalizeAssistantThinkingBudgetInput,
  resolveAssistantReasoningControl,
  resolveAssistantReasoningPreferredKind,
  type AssistantReasoningControl,
} from "@/features/shared/assistant/assistant-reasoning-support";

import {
  buildAssistantPreferencesPayload,
  isAssistantPreferencesDirty,
  normalizeAssistantPreferencesDraft,
  normalizeAssistantMaxOutputTokenDraft,
  toAssistantPreferencesDraft,
  type AssistantPreferencesDraft,
  type AssistantProviderOption,
} from "@/features/settings/components/assistant/preferences/assistant-preferences-support";

type AssistantPreferencesFormProps = {
  emptyStateText: string;
  formDescription: string;
  inheritedPreferences?: AssistantPreferences;
  isPending: boolean;
  onDirtyChange?: (isDirty: boolean) => void;
  onSubmit: (payload: AssistantPreferencesUpdatePayload) => void;
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
  const [draft, setDraft] = useState<AssistantPreferencesDraft>(() => {
    const initialDraft = toAssistantPreferencesDraft(preferences);
    const initialControl = resolvePreferencesReasoningControl(
      initialDraft,
      inheritedPreferences,
      providerOptions,
    );
    return normalizeAssistantPreferencesDraft(initialDraft, initialControl);
  });
  const reasoningControl = resolvePreferencesReasoningControl(draft, inheritedPreferences, providerOptions);
  const reasoningShapeError = buildAssistantReasoningShapeError({
    reasoningEffort: draft.defaultReasoningEffort,
    thinkingBudget: draft.defaultThinkingBudget,
    thinkingLevel: draft.defaultThinkingLevel,
  });
  const isDirty = isAssistantPreferencesDirty(draft, preferences, reasoningControl);

  const updateDraft = (updater: (current: AssistantPreferencesDraft) => AssistantPreferencesDraft) =>
    setDraft((current) => {
      const nextDraft = updater(current);
      const nextControl = resolvePreferencesReasoningControl(
        nextDraft,
        inheritedPreferences,
        providerOptions,
      );
      return normalizeAssistantPreferencesDraft(nextDraft, nextControl);
    });

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form
      className="panel-muted space-y-10 p-10"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(buildAssistantPreferencesPayload(draft, reasoningControl));
      }}
    >
      <div className="rounded-2xl bg-[rgba(248,243,235,0.92)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        {formDescription}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <AssistantProviderField draft={draft} providerOptions={providerOptions} updateDraft={updateDraft} />
        <AssistantModelField
          draft={draft}
          inheritedModelName={inheritedPreferences?.default_model_name ?? undefined}
          updateDraft={updateDraft}
        />
        <AssistantMaxOutputTokensField
          draft={draft}
          inheritedMaxOutputTokens={inheritedPreferences?.default_max_output_tokens ?? undefined}
          placeholderText={placeholderText}
          updateDraft={updateDraft}
        />
        <AssistantReasoningField
          draft={draft}
          reasoningControl={reasoningControl}
          reasoningShapeError={reasoningShapeError}
          updateDraft={updateDraft}
        />
      </div>
      {showCredentialEmptyState ? (
        <div className="rounded-2xl bg-[rgba(183,121,31,0.08)] px-4 py-3 text-sm text-[var(--accent-warning)]">
          {emptyStateText}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button className="ink-button" disabled={isPending || !isDirty || reasoningShapeError !== null} type="submit">
          {isPending ? "保存中..." : reasoningShapeError ? "先处理冲突字段" : "保存设置"}
        </button>
        <button
          className="ink-button-secondary"
          disabled={isPending || !isDirty}
          onClick={() => {
            const resetDraft = toAssistantPreferencesDraft(preferences);
            const resetControl = resolvePreferencesReasoningControl(
              resetDraft,
              inheritedPreferences,
              providerOptions,
            );
            setDraft(normalizeAssistantPreferencesDraft(resetDraft, resetControl));
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
  updateDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  providerOptions: AssistantProviderOption[];
  updateDraft: (updater: (current: AssistantPreferencesDraft) => AssistantPreferencesDraft) => void;
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
          updateDraft((current) => ({
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
  updateDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  inheritedModelName?: string;
  updateDraft: (updater: (current: AssistantPreferencesDraft) => AssistantPreferencesDraft) => void;
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
          updateDraft((current) => ({
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
  updateDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  inheritedMaxOutputTokens?: number;
  placeholderText: string;
  updateDraft: (updater: (current: AssistantPreferencesDraft) => AssistantPreferencesDraft) => void;
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
          updateDraft((current) => ({
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

function AssistantReasoningField({
  draft,
  reasoningControl,
  reasoningShapeError,
  updateDraft,
}: Readonly<{
  draft: AssistantPreferencesDraft;
  reasoningControl: AssistantReasoningControl;
  reasoningShapeError: string | null;
  updateDraft: (updater: (current: AssistantPreferencesDraft) => AssistantPreferencesDraft) => void;
}>) {
  const conflictNotice = reasoningShapeError ? (
    <div className="rounded-2xl bg-[rgba(183,121,31,0.08)] px-4 py-3 text-[12px] leading-5 text-[var(--accent-warning)]">
      当前偏好里存在历史冲突字段：{reasoningShapeError}。先清掉冲突项，再保存新的思考设置。
      <div className="mt-2">
        <button
          className="ink-button-secondary"
          type="button"
          onClick={() =>
            updateDraft((current) => ({
              ...current,
              defaultReasoningEffort: "",
              defaultThinkingBudget: "",
              defaultThinkingLevel: "",
            }))}
        >
          清空冲突设置
        </button>
      </div>
    </div>
  ) : null;
  if (reasoningControl.kind === "none") {
    return (
      <div className="space-y-2 lg:col-span-2">
        <p className="text-sm font-medium text-[var(--text-primary)]">思考设置</p>
        {conflictNotice}
        <div className="rounded-2xl bg-[rgba(248,243,235,0.92)] px-4 py-3 text-[12px] leading-5 text-[var(--text-secondary)]">
          {reasoningControl.description}
        </div>
      </div>
    );
  }
  if (reasoningControl.kind === "gemini_budget") {
    return (
      <div className="space-y-2 lg:col-span-2">
        <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="assistant-default-thinking-budget">
          {reasoningControl.title}
        </label>
        {conflictNotice}
        <div className="flex flex-wrap gap-2">
          <ReasoningPresetButton
            active={draft.defaultThinkingBudget === ""}
            label="跟随默认"
            onClick={() =>
              updateDraft((current) => ({
                ...current,
                defaultThinkingBudget: "",
              }))}
          />
          {reasoningControl.allowDisable ? (
            <ReasoningPresetButton
              active={draft.defaultThinkingBudget === "0"}
              label="关闭思考"
              onClick={() =>
                updateDraft((current) => ({
                  ...current,
                  defaultThinkingBudget: "0",
                }))}
            />
          ) : null}
          {reasoningControl.allowDynamic ? (
            <ReasoningPresetButton
              active={draft.defaultThinkingBudget === "-1"}
              label="动态思考"
              onClick={() =>
                updateDraft((current) => ({
                  ...current,
                  defaultThinkingBudget: "-1",
                }))}
            />
          ) : null}
        </div>
        <input
          className="ink-input"
          id="assistant-default-thinking-budget"
          inputMode="numeric"
          onChange={(event) =>
            updateDraft((current) => ({
              ...current,
              defaultThinkingBudget: normalizeAssistantThinkingBudgetInput(event.target.value),
            }))}
          placeholder={reasoningControl.placeholder}
          value={draft.defaultThinkingBudget}
        />
        <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
          {reasoningControl.description}
        </p>
      </div>
    );
  }
  const optionValue = reasoningControl.kind === "openai"
    ? draft.defaultReasoningEffort
    : draft.defaultThinkingLevel;

  return (
    <div className="space-y-2 lg:col-span-2">
      <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="assistant-default-reasoning">
        {reasoningControl.title}
      </label>
      {conflictNotice}
      <AppSelect
        className="min-w-0"
        id="assistant-default-reasoning"
        options={reasoningControl.options}
        value={optionValue}
        onChange={(value) =>
          updateDraft((current) => ({
            ...current,
            ...(reasoningControl.kind === "openai"
              ? { defaultReasoningEffort: value }
              : { defaultThinkingLevel: value }),
          }))}
      />
      <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
        {reasoningControl.description}
      </p>
    </div>
  );
}

function ReasoningPresetButton({
  active,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={`rounded-full border px-3 py-1.5 text-[12px] transition ${
        active
          ? "border-[rgba(46,111,106,0.24)] bg-[rgba(46,111,106,0.1)] text-[var(--accent-ink)]"
          : "border-[rgba(101,92,82,0.12)] bg-white text-[var(--text-secondary)] hover:border-[rgba(46,111,106,0.18)]"
      }`}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function resolvePreferencesReasoningControl(
  draft: AssistantPreferencesDraft,
  inheritedPreferences: AssistantPreferences | undefined,
  providerOptions: AssistantProviderOption[],
) {
  const effectiveProvider = draft.defaultProvider.trim() || inheritedPreferences?.default_provider?.trim() || "";
  const selectedProviderOption = providerOptions.find((item) => item.value === effectiveProvider);
  const effectiveModelName = draft.defaultModelName.trim()
    || inheritedPreferences?.default_model_name?.trim()
    || selectedProviderOption?.defaultModel?.trim()
    || "";
  const apiDialect = selectedProviderOption?.apiDialect ?? null;
  const preferredKind = resolveAssistantReasoningPreferredKind({
    reasoningEffort: draft.defaultReasoningEffort || (inheritedPreferences?.default_reasoning_effort ?? ""),
    thinkingBudget: draft.defaultThinkingBudget || (
      inheritedPreferences?.default_thinking_budget == null
        ? ""
        : String(inheritedPreferences.default_thinking_budget)
    ),
    thinkingLevel: draft.defaultThinkingLevel || (inheritedPreferences?.default_thinking_level ?? ""),
  });
  return resolveAssistantReasoningControl({
    apiDialect,
    modelName: effectiveModelName,
    preferredKind,
  });
}
