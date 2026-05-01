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
    const initialControl = resolvePreferencesReasoningControl(initialDraft, inheritedPreferences, providerOptions);
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
      const nextControl = resolvePreferencesReasoningControl(nextDraft, inheritedPreferences, providerOptions);
      return normalizeAssistantPreferencesDraft(nextDraft, nextControl);
    });

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(buildAssistantPreferencesPayload(draft, reasoningControl));
      }}
    >
      <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{formDescription}</p>

      {/* Connection Card */}
      <div
        className="rounded-md p-3 space-y-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <div className="flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round">
            <path d="M5 12h14" />
            <path d="M12 5v14" />
          </svg>
          <span className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>连接配置</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField label="默认连接">
            <AppSelect
              className="min-w-0"
              emptyText="暂无可用连接"
              id="assistant-default-provider"
              options={providerOptions}
              value={draft.defaultProvider}
              onChange={(value) => updateDraft((current) => ({ ...current, defaultProvider: value }))}
            />
            <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>建议直接从可用连接里选择</p>
          </FormField>

          <FormField label="默认模型">
            <input
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              onChange={(event) => updateDraft((current) => ({ ...current, defaultModelName: event.target.value }))}
              placeholder={inheritedPreferences?.default_model_name ? `当前继承：${inheritedPreferences.default_model_name}` : "例如：gpt-4.1-mini"}
              value={draft.defaultModelName}
            />
            <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>通常留空即可</p>
          </FormField>
        </div>
      </div>

      {/* Parameters Card */}
      <div
        className="rounded-md p-3 space-y-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <div className="flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v6m0 6v6m4.22-10.22 4.24-4.24M6.34 6.34 2.1 2.1m17.8 17.8-4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.07-4.93-4.24 4.24M6.34 6.34l-4.24-4.24" />
          </svg>
          <span className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>生成参数</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField label="单次回复上限">
            <input
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              inputMode="numeric"
              min={128}
              onChange={(event) => updateDraft((current) => ({ ...current, defaultMaxOutputTokens: normalizeAssistantMaxOutputTokenDraft(event.target.value) }))}
              placeholder={inheritedPreferences?.default_max_output_tokens ? `当前继承：${inheritedPreferences.default_max_output_tokens}` : placeholderText}
              value={draft.defaultMaxOutputTokens}
            />
            <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>只控制单次回复长度</p>
          </FormField>
        </div>
      </div>

      {/* Reasoning Card */}
      <div
        className="rounded-md p-3 space-y-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <div className="flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round">
            <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5" />
            <path d="M8.5 8.5v.01" />
            <path d="M16 15.5v.01" />
            <path d="M12 12v.01" />
            <path d="M8 16v.01" />
            <path d="M16 8v.01" />
          </svg>
          <span className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>思考设置</span>
        </div>
        <ReasoningControl
          control={reasoningControl}
          draft={draft}
          error={reasoningShapeError}
          onUpdate={updateDraft}
        />
      </div>

      {showCredentialEmptyState ? (
        <div className="rounded-md px-3.5 py-2.5 text-[12px]" style={{ background: "var(--accent-warning-soft)", color: "var(--accent-warning)" }}>
          {emptyStateText}
        </div>
      ) : null}

      <div className="flex gap-2 pt-1">
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium transition-colors"
          disabled={isPending || !isDirty || reasoningShapeError !== null}
          style={{
            background: isDirty && !reasoningShapeError ? "var(--accent-primary)" : "var(--line-soft)",
            color: isDirty && !reasoningShapeError ? "var(--text-on-accent)" : "var(--text-tertiary)",
          }}
          type="submit"
        >
          {isPending ? "保存中..." : reasoningShapeError ? "先处理冲突" : "保存设置"}
        </button>
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium"
          disabled={isPending || !isDirty}
          onClick={() => {
            const resetDraft = toAssistantPreferencesDraft(preferences);
            const resetControl = resolvePreferencesReasoningControl(resetDraft, inheritedPreferences, providerOptions);
            setDraft(normalizeAssistantPreferencesDraft(resetDraft, resetControl));
          }}
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          type="button"
        >
          还原
        </button>
      </div>
    </form>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>{label}</label>
      {children}
    </div>
  );
}

function ReasoningControl({
  control,
  draft,
  error,
  onUpdate,
}: {
  control: AssistantReasoningControl;
  draft: AssistantPreferencesDraft;
  error: string | null;
  onUpdate: (updater: (current: AssistantPreferencesDraft) => AssistantPreferencesDraft) => void;
}) {
  if (error) {
    return (
      <div className="rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-warning-soft)", color: "var(--accent-warning)" }}>
        {error}
        <button
          className="ml-2 text-[10px] underline"
          onClick={() => onUpdate((current) => ({ ...current, defaultReasoningEffort: "", defaultThinkingBudget: "", defaultThinkingLevel: "" }))}
        >
          清空冲突
        </button>
      </div>
    );
  }

  if (control.kind === "none") {
    return <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{control.description}</p>;
  }

  if (control.kind === "gemini_budget") {
    return (
      <div className="space-y-1.5">
        <div className="flex gap-1.5">
          <ReasoningButton active={draft.defaultThinkingBudget === ""} label="跟随默认" onClick={() => onUpdate((c) => ({ ...c, defaultThinkingBudget: "" }))} />
          {control.allowDisable && <ReasoningButton active={draft.defaultThinkingBudget === "0"} label="关闭" onClick={() => onUpdate((c) => ({ ...c, defaultThinkingBudget: "0" }))} />}
          {control.allowDynamic && <ReasoningButton active={draft.defaultThinkingBudget === "-1"} label="动态" onClick={() => onUpdate((c) => ({ ...c, defaultThinkingBudget: "-1" }))} />}
        </div>
        <input
          className="w-full h-8 px-3 rounded-md text-[12px]"
          style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
          inputMode="numeric"
          onChange={(event) => onUpdate((c) => ({ ...c, defaultThinkingBudget: normalizeAssistantThinkingBudgetInput(event.target.value) }))}
          placeholder={control.placeholder}
          value={draft.defaultThinkingBudget}
        />
        <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{control.description}</p>
      </div>
    );
  }

  const optionValue = control.kind === "openai" ? draft.defaultReasoningEffort : draft.defaultThinkingLevel;

  return (
    <div className="space-y-1.5">
      <AppSelect
        className="min-w-0"
        id="assistant-default-reasoning"
        options={control.options}
        value={optionValue}
        onChange={(value) => onUpdate((c) => ({ ...c, ...(control.kind === "openai" ? { defaultReasoningEffort: value } : { defaultThinkingLevel: value }) }))}
      />
      <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{control.description}</p>
    </div>
  );
}

function ReasoningButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      className="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
      onClick={onClick}
      style={{
        background: active ? "var(--accent-primary-soft)" : "var(--line-soft)",
        color: active ? "var(--accent-primary)" : "var(--text-tertiary)",
        border: active ? "1px solid var(--accent-primary-muted)" : "1px solid var(--line-medium)",
      }}
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
    thinkingBudget: draft.defaultThinkingBudget || (inheritedPreferences?.default_thinking_budget == null ? "" : String(inheritedPreferences.default_thinking_budget)),
    thinkingLevel: draft.defaultThinkingLevel || (inheritedPreferences?.default_thinking_level ?? ""),
  });
  return resolveAssistantReasoningControl({ apiDialect, modelName: effectiveModelName, preferredKind });
}
