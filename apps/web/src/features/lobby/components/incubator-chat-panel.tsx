"use client";

import type { KeyboardEvent } from "react";

import { IncubatorChatDraftPanel } from "@/features/lobby/components/incubator-chat-draft-panel";
import {
  INCUBATOR_INPUT_MAX_LENGTH,
  INCUBATOR_PROMPT_SUGGESTIONS,
} from "@/features/lobby/components/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator-page-model";

type ChatModePanelProps = {
  model: IncubatorChatModel;
};

type ComposerSectionProps = {
  canSubmit: boolean;
  isResponding: boolean;
  model: IncubatorChatModel;
};

type VisibleChatMessage = IncubatorChatModel["messages"][number] & {
  role: "assistant" | "user";
};

export function ChatModePanel({ model }: Readonly<ChatModePanelProps>) {
  const visibleMessages = model.messages.filter(isVisibleConversationMessage);
  const canSubmit = buildCanSubmit(model);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.38fr)_minmax(320px,0.92fr)]">
      <section className="panel-shell flex min-h-[720px] flex-col overflow-hidden">
        <ChatPanelHeader onSelectPrompt={model.submitPrompt} />
        <ChatTranscript messages={visibleMessages} />
        <ChatComposerSection
          canSubmit={canSubmit}
          isResponding={model.isResponding}
          model={model}
        />
      </section>
      <IncubatorChatDraftPanel
        createMutation={model.createMutation}
        draftMutation={model.draftMutation}
        hasUserMessage={model.hasUserMessage}
        isDraftStale={model.isDraftStale}
        onProjectNameChange={model.setProjectName}
        onSyncDraft={model.syncDraft}
        projectName={model.projectName}
      />
    </div>
  );
}

function ChatPanelHeader({
  onSelectPrompt,
}: {
  onSelectPrompt: (prompt: string) => Promise<void>;
}) {
  return (
    <header className="border-b border-[var(--line-soft)] px-6 py-5">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">
          聊天创建
        </p>
        <h2 className="font-serif text-2xl font-semibold text-[var(--text-primary)]">
          先聊出一个能写下去的故事
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
          你可以先问题材、节奏、开局钩子，也可以直接丢一个模糊想法。左边负责共创，右边负责沉淀项目草稿。
        </p>
      </div>
      <PromptSuggestionBar onSelect={(prompt) => void onSelectPrompt(prompt)} />
    </header>
  );
}

function ChatTranscript({
  messages,
}: {
  messages: VisibleChatMessage[];
}) {
  return (
    <div aria-live="polite" className="flex-1 overflow-y-auto px-6 py-5">
      <div className="space-y-4">
        {messages.map((message) => (
          <MessageBubble
            content={message.content}
            key={message.id}
            role={message.role}
            status={message.status}
          />
        ))}
      </div>
    </div>
  );
}

function ChatComposerSection({
  canSubmit,
  isResponding,
  model,
}: ComposerSectionProps) {
  return (
    <footer className="border-t border-[var(--line-soft)] px-6 py-5">
      <label className="block">
        <span className="label-text">当前想法</span>
        <textarea
          autoComplete="off"
          className="ink-textarea"
          maxLength={INCUBATOR_INPUT_MAX_LENGTH}
          name="incubatorMessage"
          placeholder="例如：我想写女主成长文，但不要太套路，最好开局就有钩子…"
          rows={5}
          value={model.composerText}
          onChange={(event) => model.setComposerText(event.target.value)}
          onKeyDown={(event) => handleComposerKeyDown(event, canSubmit, model)}
        />
      </label>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-[var(--text-secondary)]">
          {model.composerText.length} / {INCUBATOR_INPUT_MAX_LENGTH}
          {" · "}
          `Ctrl/Cmd + Enter` 发送
        </p>
        <button
          className="ink-button"
          disabled={!canSubmit}
          onClick={() => void model.submitPrompt(model.composerText)}
          type="button"
        >
          {isResponding ? "AI 回复中…" : "发送给 AI"}
        </button>
      </div>
      <ChatAdvancedSettings model={model} />
    </footer>
  );
}

function ChatAdvancedSettings({ model }: { model: IncubatorChatModel }) {
  return (
    <details className="mt-4 rounded-3xl border border-[var(--line-soft)] bg-[rgba(255,255,255,0.5)] p-4">
      <summary className="cursor-pointer text-sm font-medium text-[var(--text-primary)]">
        高级设置
      </summary>
      <div className="mt-4 grid gap-4">
        <TextSettingField
          label="模型提供商"
          name="provider"
          value={model.settings.provider}
          onChange={(value) => updateChatSettings(model, "provider", value)}
        />
        <TextSettingField
          label="模型名（可选）"
          name="modelName"
          placeholder="例如：gpt-4.1…"
          value={model.settings.modelName}
          onChange={(value) => updateChatSettings(model, "modelName", value)}
        />
        <label className="flex items-start gap-3 rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3">
          <input
            checked={model.settings.allowSystemCredentialPool}
            className="mt-1 size-4 accent-[var(--accent-ink)]"
            onChange={(event) =>
              updateChatSettings(model, "allowSystemCredentialPool", event.target.checked)
            }
            type="checkbox"
          />
          <span className="space-y-1">
            <span className="block text-sm font-medium text-[var(--text-primary)]">
              创建后允许系统凭证池
            </span>
            <span className="block text-sm leading-6 text-[var(--text-secondary)]">
              只影响项目创建后的运行时策略，不影响当前聊天结果。
            </span>
          </span>
        </label>
      </div>
    </details>
  );
}

function TextSettingField({
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

function PromptSuggestionBar({
  onSelect,
}: {
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {INCUBATOR_PROMPT_SUGGESTIONS.map((prompt) => (
        <button className="ink-tab" key={prompt} onClick={() => onSelect(prompt)} type="button">
          {prompt}
        </button>
      ))}
    </div>
  );
}

function MessageBubble({
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
  const statusClassName =
    status === "error"
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

function buildCanSubmit(model: IncubatorChatModel) {
  return (
    model.composerText.trim().length > 0 &&
    !model.isResponding &&
    !model.draftMutation.isPending
  );
}

function isVisibleConversationMessage(
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

function handleComposerKeyDown(
  event: KeyboardEvent<HTMLTextAreaElement>,
  canSubmit: boolean,
  model: IncubatorChatModel,
) {
  if (!canSubmit) {
    return;
  }
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    void model.submitPrompt(model.composerText);
  }
}
