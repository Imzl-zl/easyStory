"use client";

import { useEffect, useEffectEvent, useRef } from "react";
import type { KeyboardEvent, RefObject } from "react";
import { Input } from "@arco-design/web-react";
import type { RefTextAreaType } from "@arco-design/web-react/es/Input";

import { IncubatorChatDraftPanel } from "@/features/lobby/components/incubator/incubator-chat-draft-panel";
import { ChatHistoryPanel } from "@/features/lobby/components/incubator/incubator-chat-history-panel";
import { ChatAdvancedSettings } from "@/features/lobby/components/incubator/incubator-chat-settings-panel";
import {
  INCUBATOR_INPUT_MAX_LENGTH,
  shouldShowPromptSuggestions,
  shouldSubmitIncubatorComposer,
} from "@/features/lobby/components/incubator/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator/incubator-page-model";
import {
  buildCanSubmit,
  buildComposerHint,
  CredentialNoticeCard,
  isVisibleConversationMessage,
  MessageBubble,
  PromptSuggestionBar,
  resolveSubmitButtonLabel,
  type VisibleChatMessage,
} from "@/features/lobby/components/incubator/incubator-chat-panel-support";

type ChatModePanelProps = {
  model: IncubatorChatModel;
};

type ComposerSectionProps = {
  canSubmit: boolean;
  composerRef: RefObject<RefTextAreaType | null>;
  isCredentialLoading: boolean;
  isResponding: boolean;
  model: IncubatorChatModel;
};

export function ChatModePanel({ model }: Readonly<ChatModePanelProps>) {
  const visibleMessages = model.messages.filter(isVisibleConversationMessage);
  const canSubmit = buildCanSubmit(model);
  const composerRef = useRef<RefTextAreaType | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const showPromptSuggestions = model.credentialState === "ready"
    && model.canChat
    && shouldShowPromptSuggestions(model.hasUserMessage)
    && !model.isResponding;
  const disablePromptSuggestions = !model.canChat || model.isCredentialLoading;
  const lastMessage = visibleMessages.at(-1);
  const syncTranscriptToBottom = useEffectEvent(() => {
    const node = transcriptRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  });

  useEffect(() => {
    syncTranscriptToBottom();
  }, [
    lastMessage?.content,
    lastMessage?.id,
    lastMessage?.status,
    model.activeConversationId,
    showPromptSuggestions,
    visibleMessages.length,
  ]);

  return (
    <div className="grid h-full min-h-0 gap-2 lg:gap-2.5 lg:grid-cols-[minmax(312px,352px)_minmax(0,1fr)] xl:grid-cols-[minmax(324px,368px)_minmax(0,1fr)] 2xl:grid-cols-[minmax(336px,384px)_minmax(0,1fr)]">
      <section className="panel-shell order-1 flex min-h-[440px] flex-col overflow-hidden md:min-h-[500px] lg:order-2 lg:h-full lg:min-h-0">
        <ChatPanelHeader model={model} />
        <ChatTranscript
          disablePromptSuggestions={disablePromptSuggestions}
          messages={visibleMessages}
          showPromptSuggestions={showPromptSuggestions}
          transcriptRef={transcriptRef}
          onSelectPrompt={(prompt) => {
            model.applyPromptSuggestion(prompt);
            composerRef.current?.focus();
          }}
        />
        <ChatComposerSection
          canSubmit={canSubmit}
          composerRef={composerRef}
          isCredentialLoading={model.isCredentialLoading}
          isResponding={model.isResponding}
          model={model}
        />
      </section>
      <IncubatorChatDraftPanel
        canCompleteWithAi={model.canCompleteDraftWithAi}
        createMutation={model.createMutation}
        draft={model.draft}
        draftMutation={model.draftMutation}
        hasUserMessage={model.hasUserMessage}
        isDraftStale={model.isDraftStale}
        isCompletingWithAi={model.isCompletingDraftWithAi}
        onCompleteWithAi={model.completeDraftWithAi}
        onProjectNameChange={model.setProjectName}
        onSyncDraft={model.syncDraft}
        projectName={model.projectName}
      />
    </div>
  );
}

function ChatPanelHeader({
  model,
}: {
  model: IncubatorChatModel;
}) {
  return (
    <header className="relative z-10 border-b border-line-soft px-3 py-1.5 md:px-4 md:py-2 xl:px-5">
      <div className="flex flex-wrap items-center gap-1.5 md:gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <h2 className="text-[13px] font-semibold text-text-primary">AI 聊天</h2>
          {model.isCredentialLoading ? (
            <span className="rounded-full bg-surface-hover px-2 py-0.5 text-[10px] leading-4 text-text-secondary">
              正在准备
            </span>
          ) : null}
        </div>
        <div className="ml-auto flex min-w-0 flex-wrap items-center justify-end gap-1.5">
          <ChatHistoryPanel model={model} />
          <ChatAdvancedSettings model={model} />
        </div>
      </div>
      {model.credentialNotice ? (
        <div className="mt-2">
          <CredentialNoticeCard
            credentialSettingsHref={model.credentialSettingsHref}
            message={model.credentialNotice}
          />
        </div>
      ) : null}
    </header>
  );
}

function ChatTranscript({
  disablePromptSuggestions,
  messages,
  showPromptSuggestions,
  transcriptRef,
  onSelectPrompt,
}: {
  disablePromptSuggestions: boolean;
  messages: VisibleChatMessage[];
  showPromptSuggestions: boolean;
  transcriptRef: RefObject<HTMLDivElement | null>;
  onSelectPrompt: (prompt: string) => void;
}) {
  return (
    <div
      aria-live="polite"
      className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain bg-[var(--bg-panel-warm-gradient)] px-3 py-1.5 md:px-4 md:py-2 xl:px-5"
      ref={transcriptRef}
    >
      <div className="mx-auto flex min-h-full w-full max-w-[980px] flex-col gap-1.5">
        {messages.map((message) => (
          <MessageBubble
            content={message.content}
            hookResults={message.hookResults}
            key={message.id}
            role={message.role}
            status={message.status}
          />
        ))}
        {showPromptSuggestions ? (
          <section className="mt-0.5 rounded-2xl bg-glass shadow-glass p-2.5 shadow-sm">
            <p className="text-[12.5px] font-medium text-text-primary">不知道怎么开始？</p>
            <p className="mt-1 text-[11.5px] leading-5 text-text-secondary">
              先选一句示例，再按你的想法继续改。
            </p>
            <PromptSuggestionBar disabled={disablePromptSuggestions} onSelect={onSelectPrompt} />
          </section>
        ) : null}
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
}: Readonly<ComposerSectionProps>) {
  return (
    <footer className="border-t border-line-soft bg-glass px-3 py-1.5 md:px-4 md:py-2 xl:px-5">
      <div className="rounded-2xl bg-glass shadow-glass-heavy px-2.5 py-1.5 shadow-sm transition-[border-color,box-shadow,background-color] focus-within:border-accent-primary/25 focus-within:ring-3 focus-within:ring-accent-primary/10">
        <label className="block">
          <span className="sr-only">继续聊</span>
          <Input.TextArea
            autoSize={{ maxRows: 6, minRows: 2 }}
            autoComplete="off"
            className="w-full text-[13px] leading-6"
            maxLength={INCUBATOR_INPUT_MAX_LENGTH}
            name="incubatorMessage"
            placeholder="例如：我想写一篇女主成长小说，开局就要有冲突…"
            ref={composerRef}
            value={model.composerText}
            onChange={(value) => model.setComposerText(value)}
            onKeyDown={(event) => handleComposerKeyDown(event, canSubmit, model)}
          />
        </label>
        <div className="mt-1.5 flex flex-wrap items-center justify-between gap-1.5">
          <p className="flex-1 text-[11px] leading-5 text-text-secondary">
            {buildComposerHint(
              model.composerText.length,
              model.credentialState,
              model.canChat,
              isCredentialLoading,
            )}
          </p>
          <button
            className="ink-button"
            disabled={!canSubmit}
            type="button"
            onClick={() => submitComposerText(canSubmit, model)}
          >
            {resolveSubmitButtonLabel(isCredentialLoading, isResponding)}
          </button>
        </div>
      </div>
    </footer>
  );
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
