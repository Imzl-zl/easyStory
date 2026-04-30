"use client";

import { useEffect, useEffectEvent, useRef, useState } from "react";
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

/* ------------------------------------------------------------------ */
/*  Chat Mode Panel — 中央聚焦式布局                                  */
/* ------------------------------------------------------------------ */

export function ChatModePanel({ model }: Readonly<ChatModePanelProps>) {
  const visibleMessages = model.messages.filter(isVisibleConversationMessage);
  const canSubmit = buildCanSubmit(model);
  const composerRef = useRef<RefTextAreaType | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const showPromptSuggestions =
    model.credentialState === "ready" &&
    model.canChat &&
    shouldShowPromptSuggestions(model.hasUserMessage) &&
    !model.isResponding;
  const disablePromptSuggestions = !model.canChat || model.isCredentialLoading;
  const lastMessage = visibleMessages.at(-1);
  const [draftOpen, setDraftOpen] = useState(false);

  const syncTranscriptToBottom = useEffectEvent(() => {
    const node = transcriptRef.current;
    if (!node) return;
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
    <div className="incubator-chat">
      {/* 中央对话区 */}
      <div className="incubator-chat-main">
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
        <ChatComposer
          canSubmit={canSubmit}
          composerRef={composerRef}
          isCredentialLoading={model.isCredentialLoading}
          isResponding={model.isResponding}
          model={model}
        />
      </div>

      {/* 草稿面板触发器 */}
      <DraftTrigger
        draft={model.draft}
        draftOpen={draftOpen}
        hasUserMessage={model.hasUserMessage}
        onToggle={() => setDraftOpen(!draftOpen)}
      />

      {/* 底部升起式草稿面板 */}
      <div className={`incubator-draft-drawer ${draftOpen ? "open" : ""}`}>
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
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Chat Transcript — 中央滚动区                                      */
/* ------------------------------------------------------------------ */

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
  const hasMessages = messages.length > 0;

  return (
    <div
      aria-live="polite"
      className="incubator-transcript"
      ref={transcriptRef}
    >
      <div className="incubator-transcript-inner">
        {/* 空状态 — 大标题引导 */}
        {!hasMessages && !showPromptSuggestions && (
          <EmptyState />
        )}

        {/* 消息流 */}
        <div className="incubator-messages">
          {messages.map((message) => (
            <MessageBubble
              content={message.content}
              hookResults={message.hookResults}
              key={message.id}
              role={message.role}
              status={message.status}
            />
          ))}
        </div>

        {/* 提示词建议 */}
        {showPromptSuggestions && (
          <div className="incubator-suggestions">
            <PromptSuggestionSection
              disabled={disablePromptSuggestions}
              onSelect={onSelectPrompt}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Empty State — 杂志风大标题                                        */
/* ------------------------------------------------------------------ */

function EmptyState() {
  return (
    <div className="incubator-empty">
      <div className="incubator-empty-kicker">新项目</div>
      <h1 className="incubator-empty-title">
        从这里开始<br />你的故事
      </h1>
      <p className="incubator-empty-body">
        描述你想写的故事——题材、主角、世界观，<br />
        AI 会帮你整理成完整的项目草稿。
      </p>
      <div className="incubator-empty-line" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Prompt Suggestion Section                                         */
/* ------------------------------------------------------------------ */

function PromptSuggestionSection({
  disabled,
  onSelect,
}: {
  disabled?: boolean;
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="incubator-suggestion-card">
      <p className="incubator-suggestion-label">不知道怎么开始？</p>
      <PromptSuggestionBar disabled={disabled} onSelect={onSelect} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Chat Composer — 底部中央输入                                      */
/* ------------------------------------------------------------------ */

function ChatComposer({
  canSubmit,
  composerRef,
  isCredentialLoading,
  isResponding,
  model,
}: {
  canSubmit: boolean;
  composerRef: RefObject<RefTextAreaType | null>;
  isCredentialLoading: boolean;
  isResponding: boolean;
  model: IncubatorChatModel;
}) {
  return (
    <div className="incubator-composer">
      <div className="incubator-composer-inner">
        <div className="incubator-composer-field">
          <Input.TextArea
            autoSize={{ maxRows: 6, minRows: 1 }}
            autoComplete="off"
            className="incubator-composer-input"
            maxLength={INCUBATOR_INPUT_MAX_LENGTH}
            name="incubatorMessage"
            placeholder="描述你想写的故事..."
            ref={composerRef}
            value={model.composerText}
            onChange={(value) => model.setComposerText(value)}
            onKeyDown={(event) => handleComposerKeyDown(event, canSubmit, model)}
          />
          <button
            className="incubator-composer-send"
            disabled={!canSubmit}
            type="button"
            onClick={() => submitComposerText(canSubmit, model)}
          >
            <svg aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
        <div className="incubator-composer-meta">
          <span className="incubator-composer-hint">
            {buildComposerHint(
              model.composerText.length,
              model.credentialState,
              model.canChat,
              isCredentialLoading,
            )}
          </span>
          <div className="incubator-composer-tools">
            <ChatHistoryPanel model={model} />
            <ChatAdvancedSettings model={model} />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Draft Trigger — 草稿面板开关                                      */
/* ------------------------------------------------------------------ */

function DraftTrigger({
  draft,
  draftOpen,
  hasUserMessage,
  onToggle,
}: {
  draft: { setting_completeness?: { status: string } } | null;
  draftOpen: boolean;
  hasUserMessage: boolean;
  onToggle: () => void;
}) {
  if (!hasUserMessage && !draft) return null;

  const status = draft?.setting_completeness?.status;
  const statusDot = status === "complete" ? "complete" : status === "partial" ? "partial" : "draft";

  return (
    <button className={`incubator-draft-trigger ${draftOpen ? "open" : ""}`} onClick={onToggle} type="button">
      <span className={`incubator-draft-dot ${statusDot}`} />
      <span className="incubator-draft-label">{draftOpen ? "收起草稿" : "查看草稿"}</span>
      <svg aria-hidden="true" className="incubator-draft-arrow" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
        <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function handleComposerKeyDown(
  event: KeyboardEvent<HTMLTextAreaElement>,
  canSubmit: boolean,
  model: IncubatorChatModel,
) {
  if (
    !canSubmit ||
    !shouldSubmitIncubatorComposer({
      isComposing: event.nativeEvent.isComposing,
      key: event.key,
      shiftKey: event.shiftKey,
    })
  ) {
    return;
  }
  event.preventDefault();
  submitComposerText(canSubmit, model);
}

function submitComposerText(canSubmit: boolean, model: IncubatorChatModel) {
  if (!canSubmit) return;
  void model.submitPrompt(model.composerText);
}
