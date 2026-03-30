"use client";

import { useEffect, useEffectEvent, useRef } from "react";
import type { KeyboardEvent, RefObject } from "react";

import { IncubatorChatDraftPanel } from "@/features/lobby/components/incubator-chat-draft-panel";
import { ChatHistoryPanel } from "@/features/lobby/components/incubator-chat-history-panel";
import { ChatAdvancedSettings } from "@/features/lobby/components/incubator-chat-settings-panel";
import {
  INCUBATOR_INPUT_MAX_LENGTH,
  shouldShowPromptSuggestions,
  shouldSubmitIncubatorComposer,
} from "@/features/lobby/components/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator-page-model";
import {
  buildCanSubmit,
  buildComposerHint,
  CredentialNoticeCard,
  isVisibleConversationMessage,
  MessageBubble,
  PromptSuggestionBar,
  resolveSubmitButtonLabel,
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
    <div className="grid h-full min-h-0 gap-2 lg:gap-2.5 lg:grid-cols-[minmax(372px,408px)_minmax(0,1fr)] xl:grid-cols-[minmax(388px,424px)_minmax(0,1fr)] 2xl:grid-cols-[minmax(400px,440px)_minmax(0,1fr)]">
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
        createMutation={model.createMutation}
        draft={model.draft}
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
  model,
}: {
  model: IncubatorChatModel;
}) {
  return (
    <header className="border-b border-[var(--line-soft)] px-3 py-2 md:px-4 md:py-2.5 xl:px-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-[13.5px] font-semibold text-[var(--text-primary)]">AI 聊天</h2>
            {model.isCredentialLoading ? (
              <span className="rounded-full bg-[rgba(31,27,22,0.05)] px-2 py-0.5 text-[10px] leading-4 text-[var(--text-secondary)]">
                正在准备聊天…
              </span>
            ) : null}
          </div>
          <p className="mt-0.5 text-[11px] leading-5 text-[var(--text-secondary)]">
            先聊想法，再整理草稿。
          </p>
        </div>
      </div>
      <div className="mt-2 space-y-1.5">
        <ChatHistoryPanel model={model} />
        {model.credentialNotice ? (
          <CredentialNoticeCard
            credentialSettingsHref={model.credentialSettingsHref}
            message={model.credentialNotice}
          />
        ) : null}
        <ChatAdvancedSettings model={model} />
      </div>
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
      className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain bg-[linear-gradient(180deg,rgba(255,255,255,0.58)_0%,rgba(247,240,229,0.3)_100%)] px-3 py-2 md:px-4 md:py-2.5 xl:px-5"
      ref={transcriptRef}
    >
      <div className="mx-auto flex min-h-full w-full max-w-[900px] flex-col gap-1.5">
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
          <section className="mt-0.5 rounded-[18px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.82)] p-2.5 shadow-[0_10px_20px_rgba(58,45,29,0.05)]">
            <p className="text-[12.5px] font-medium text-[var(--text-primary)]">不知道怎么开始？</p>
            <p className="mt-1 text-[11.5px] leading-5 text-[var(--text-secondary)]">
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
    <footer className="border-t border-[var(--line-soft)] bg-[rgba(248,243,235,0.82)] px-3 py-2 md:px-4 xl:px-5">
      <div className="rounded-[18px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.9)] px-2.5 py-1.5 shadow-[0_8px_18px_rgba(58,45,29,0.05)] transition-[border-color,box-shadow,background-color] focus-within:border-[rgba(46,111,106,0.24)] focus-within:shadow-[0_0_0_3px_rgba(46,111,106,0.1)]">
        <label className="block">
          <span className="sr-only">继续聊</span>
          <textarea
            autoComplete="off"
            className="min-h-[52px] max-h-[120px] w-full resize-none overflow-y-auto border-0 bg-transparent px-0.5 py-0 text-[13px] leading-6 text-[var(--text-primary)] outline-none focus-visible:outline-none placeholder:text-[color:var(--text-secondary)]"
            maxLength={INCUBATOR_INPUT_MAX_LENGTH}
            name="incubatorMessage"
            placeholder="例如：我想写一篇女主成长小说，开局就要有冲突…"
            ref={composerRef}
            rows={2}
            value={model.composerText}
            onChange={(event) => model.setComposerText(event.target.value)}
            onKeyDown={(event) => handleComposerKeyDown(event, canSubmit, model)}
          />
        </label>
        <div className="mt-1.5 flex flex-wrap items-center justify-between gap-1.5">
          <p className="flex-1 text-[11px] leading-5 text-[var(--text-secondary)]">
            {buildComposerHint(
              model.composerText.length,
              model.credentialState,
              model.canChat,
              isCredentialLoading,
            )}
          </p>
          <button
            className="ink-button h-9 px-3.5 text-[12.5px]"
            disabled={!canSubmit}
            onClick={() => submitComposerText(canSubmit, model)}
            type="button"
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
