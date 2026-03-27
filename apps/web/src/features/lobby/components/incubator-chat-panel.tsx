"use client";

import { useRef } from "react";
import type { RefObject } from "react";
import type { KeyboardEvent } from "react";

import { IncubatorChatDraftPanel } from "@/features/lobby/components/incubator-chat-draft-panel";
import {
  INCUBATOR_INPUT_MAX_LENGTH,
  shouldSubmitIncubatorComposer,
  shouldShowPromptSuggestions,
} from "@/features/lobby/components/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator-page-model";
import {
  buildCanSubmit,
  CredentialNoticeCard,
  isVisibleConversationMessage,
  MessageBubble,
  PromptSuggestionBar,
  ProviderSelectField,
  TextSettingField,
  type VisibleChatMessage,
} from "@/features/lobby/components/incubator-chat-panel-support";

type ChatModePanelProps = {
  model: IncubatorChatModel;
};

type ComposerSectionProps = {
  canSubmit: boolean;
  composerRef: RefObject<HTMLTextAreaElement | null>;
  isCredentialLoading: boolean;
  isResponding: boolean;
  model: IncubatorChatModel;
};

export function ChatModePanel({ model }: Readonly<ChatModePanelProps>) {
  const visibleMessages = model.messages.filter(isVisibleConversationMessage);
  const canSubmit = buildCanSubmit(model);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const showPromptSuggestions = shouldShowPromptSuggestions(model.hasUserMessage) && !model.isResponding;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(320px,0.9fr)_minmax(0,1.22fr)]">
      <IncubatorChatDraftPanel
        createMutation={model.createMutation}
        draftMutation={model.draftMutation}
        hasUserMessage={model.hasUserMessage}
        isDraftStale={model.isDraftStale}
        onProjectNameChange={model.setProjectName}
        onSyncDraft={model.syncDraft}
        projectName={model.projectName}
      />
      <section className="panel-shell order-1 flex min-h-[720px] flex-col overflow-hidden xl:order-2">
        <ChatPanelHeader
          credentialNotice={model.credentialNotice}
          credentialSettingsHref={model.credentialSettingsHref}
          disablePromptSuggestions={!model.canChat || model.isCredentialLoading}
          isCredentialLoading={model.isCredentialLoading}
          showPromptSuggestions={showPromptSuggestions}
          onSelectPrompt={(prompt) => {
            model.applyPromptSuggestion(prompt);
            composerRef.current?.focus();
          }}
        />
        <ChatTranscript messages={visibleMessages} />
        <ChatComposerSection
          canSubmit={canSubmit}
          composerRef={composerRef}
          isCredentialLoading={model.isCredentialLoading}
          isResponding={model.isResponding}
          model={model}
        />
      </section>
    </div>
  );
}

function ChatPanelHeader({
  credentialNotice,
  credentialSettingsHref,
  disablePromptSuggestions,
  isCredentialLoading,
  showPromptSuggestions,
  onSelectPrompt,
}: {
  credentialNotice: string | null;
  credentialSettingsHref: string;
  disablePromptSuggestions: boolean;
  isCredentialLoading: boolean;
  showPromptSuggestions: boolean;
  onSelectPrompt: (prompt: string) => void;
}) {
  return (
    <header className="border-b border-[var(--line-soft)] px-6 py-5">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">
          聊天共创
        </p>
        <h2 className="font-serif text-2xl font-semibold text-[var(--text-primary)]">
          先把想法聊开
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
          不用一上来就填完整设定。你可以先问题材、主角、开局钩子，也可以直接把模糊想法发过来。
        </p>
      </div>
      {isCredentialLoading ? (
        <p className="mt-4 rounded-2xl bg-[rgba(31,27,22,0.05)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          正在读取可用的模型连接…
        </p>
      ) : null}
      {credentialNotice ? (
        <CredentialNoticeCard
          credentialSettingsHref={credentialSettingsHref}
          message={credentialNotice}
        />
      ) : null}
      {showPromptSuggestions ? (
        <PromptSuggestionBar disabled={disablePromptSuggestions} onSelect={onSelectPrompt} />
      ) : null}
    </header>
  );
}

function ChatTranscript({
  messages,
}: {
  messages: VisibleChatMessage[];
}) {
  return (
    <div
      aria-live="polite"
      className="flex-1 overflow-y-auto bg-[linear-gradient(180deg,rgba(255,255,255,0.58)_0%,rgba(247,240,229,0.3)_100%)] px-6 py-6"
    >
      <div className="flex flex-col gap-4">
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
  composerRef,
  isCredentialLoading,
  isResponding,
  model,
}: ComposerSectionProps) {
  return (
    <footer className="border-t border-[var(--line-soft)] px-6 py-5">
      <label className="block">
        <span className="label-text">继续聊</span>
        <textarea
          autoComplete="off"
          className="ink-textarea"
          maxLength={INCUBATOR_INPUT_MAX_LENGTH}
          name="incubatorMessage"
          placeholder="例如：我想写女主成长文，但不要太套路，最好开局就有钩子…"
          ref={composerRef}
          rows={5}
          value={model.composerText}
          onChange={(event) => model.setComposerText(event.target.value)}
          onKeyDown={(event) => handleComposerKeyDown(event, canSubmit, model)}
        />
      </label>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-[var(--text-secondary)]">
          {buildComposerHint(model.composerText.length, isCredentialLoading, model.canChat)}
        </p>
        <button
          className="ink-button"
          disabled={!canSubmit}
          onClick={() => submitComposerText(canSubmit, model)}
          type="button"
        >
          {resolveSubmitButtonLabel(isCredentialLoading, isResponding)}
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
        {model.credentialOptions.length > 0 ? (
          <ProviderSelectField model={model} />
        ) : (
          <TextSettingField
            label="连接标识"
            name="provider"
            value={model.settings.provider}
            onChange={(value) => updateChatSettings(model, "provider", value)}
          />
        )}
        <TextSettingField
          label="模型名称（可选）"
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
              创建项目后允许使用系统连接池
            </span>
            <span className="block text-sm leading-6 text-[var(--text-secondary)]">
              只影响创建后的项目运行，不影响当前聊天结果。
            </span>
          </span>
        </label>
      </div>
    </details>
  );
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
  if (!canSubmit || !shouldSubmitIncubatorComposer({
    isComposing: event.nativeEvent.isComposing,
    key: event.key,
    shiftKey: event.shiftKey,
  })) {
    return;
  }
  event.preventDefault();
  submitComposerText(canSubmit, model);
}

function submitComposerText(canSubmit: boolean, model: IncubatorChatModel) {
  if (!canSubmit) {
    return;
  }
  void model.submitPrompt(model.composerText);
}

function buildComposerHint(
  currentLength: number,
  isCredentialLoading: boolean,
  canChat: boolean,
) {
  if (isCredentialLoading) {
    return "正在读取可用连接，稍后就能开始聊天。";
  }
  if (!canChat) {
    return "先启用一条模型连接，再继续发送。";
  }
  return `${currentLength} / ${INCUBATOR_INPUT_MAX_LENGTH} · Enter 发送，Shift+Enter 换行`;
}

function resolveSubmitButtonLabel(isCredentialLoading: boolean, isResponding: boolean) {
  if (isCredentialLoading) {
    return "正在准备聊天…";
  }
  if (isResponding) {
    return "AI 回复中…";
  }
  return "发送";
}
