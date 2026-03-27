"use client";

import Link from "next/link";

import {
  INCUBATOR_PROMPT_SUGGESTIONS,
} from "@/features/lobby/components/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator-page-model";

export type VisibleChatMessage = IncubatorChatModel["messages"][number] & {
  role: "assistant" | "user";
};

export function CredentialNoticeCard({
  credentialSettingsHref,
  message,
}: {
  credentialSettingsHref: string;
  message: string;
}) {
  return (
    <div className="mt-4 rounded-2xl bg-[rgba(183,121,31,0.12)] px-4 py-3 text-sm leading-6 text-[var(--accent-warning)]">
      <p>{message}</p>
      <Link className="mt-2 inline-flex text-sm font-medium text-[var(--accent-ink)] underline-offset-4 hover:underline" href={credentialSettingsHref}>
        去凭证中心配置
      </Link>
    </div>
  );
}

export function ProviderSelectField({ model }: { model: IncubatorChatModel }) {
  return (
    <label className="block">
      <span className="label-text">模型提供商</span>
      <select
        className="ink-input"
        name="provider"
        value={model.settings.provider || model.credentialOptions[0]?.provider || ""}
        onChange={(event) => syncProviderSelection(model, event.target.value)}
      >
        {model.credentialOptions.map((option) => (
          <option key={option.provider} value={option.provider}>
            {option.displayLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

export function TextSettingField({
  label,
  name,
  onChange,
  placeholder,
  value,
}: {
  label: string;
  name: string;
  onChange: (value: string) => void;
  placeholder?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="label-text">{label}</span>
      <input
        autoComplete="off"
        className="ink-input"
        name={name}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function PromptSuggestionBar({
  disabled,
  onSelect,
}: {
  disabled?: boolean;
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {INCUBATOR_PROMPT_SUGGESTIONS.map((prompt) => (
        <button className="ink-tab" disabled={disabled} key={prompt} onClick={() => onSelect(prompt)} type="button">
          {prompt}
        </button>
      ))}
    </div>
  );
}

export function MessageBubble({
  content,
  role,
  status,
}: {
  content: string;
  role: "assistant" | "user";
  status?: "pending" | "error";
}) {
  const isAssistant = role === "assistant";
  const className = isAssistant
    ? "bg-[rgba(255,251,245,0.94)] text-[var(--text-primary)]"
    : "bg-[rgba(46,111,106,0.12)] text-[var(--text-primary)]";
  const statusClassName = status === "error"
    ? "border-[rgba(178,65,46,0.16)] bg-[rgba(178,65,46,0.1)]"
    : "border-[var(--line-soft)]";

  return (
    <article className={`rounded-3xl border p-4 ${className} ${statusClassName}`}>
      <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]">
        {isAssistant ? "AI 助手" : "你"}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-7">{content}</p>
    </article>
  );
}

export function buildCanSubmit(model: IncubatorChatModel) {
  return model.canChat && model.composerText.trim().length > 0 && !model.isCredentialLoading && !model.isResponding && !model.draftMutation.isPending;
}

export function isVisibleConversationMessage(
  message: IncubatorChatModel["messages"][number],
): message is VisibleChatMessage {
  return !message.hidden && (message.role === "assistant" || message.role === "user");
}

function updateChatSettings<K extends keyof IncubatorChatModel["settings"]>(
  model: IncubatorChatModel,
  field: K,
  value: IncubatorChatModel["settings"][K],
) {
  model.setSettings((current) => ({ ...current, [field]: value }));
}

function syncProviderSelection(model: IncubatorChatModel, provider: string) {
  const option = model.credentialOptions.find((item) => item.provider === provider);
  model.setSettings((current) => ({
    ...current,
    modelName: option?.defaultModel ?? "",
    provider,
  }));
}
