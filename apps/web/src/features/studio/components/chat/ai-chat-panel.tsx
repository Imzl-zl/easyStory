"use client";

import { useEffect, useRef, useState } from "react";

import type {
  DocumentTreeNode,
  StudioChatLayoutMode,
} from "@/features/studio/components/page/studio-page-support";

import type { StudioChatAttachmentMeta } from "@/features/studio/components/chat/studio-chat-attachment-support";
import { StudioChatHistoryPanel } from "@/features/studio/components/chat/studio-chat-history-panel";
import { StudioChatComposer } from "@/features/studio/components/chat/studio-chat-composer";
import { StudioChatMessageBubble } from "@/features/studio/components/chat/studio-chat-message-bubble";
import { StudioChatSkillPanel } from "@/features/studio/components/chat/studio-chat-skill-panel";
import type { StudioChatSkillModel } from "@/features/studio/components/chat/studio-chat-skill-model";
import type { StudioConversationSummary } from "@/features/studio/components/chat/studio-chat-store-support";
import type {
  StudioChatMessage,
  StudioChatSettings,
  StudioProviderOption,
} from "@/features/studio/components/chat/studio-chat-support";
import { resolveStudioStatusLabel, resolveStudioStatusTone } from "@/features/studio/components/chat/studio-chat-ui-support";

type AiChatPanelProps = {
  activeConversationId: string;
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
  layoutMode?: StudioChatLayoutMode;
  composerText: string;
  conversationSummaries: StudioConversationSummary[];
  createConversation: () => void;
  credentialNotice: string | null;
  credentialSettingsHref: string;
  credentialState: "empty" | "error" | "loading" | "ready";
  currentDocumentPath: string | null;
  deleteConversation: (conversationId: string) => void;
  isCredentialLoading: boolean;
  isResponding?: boolean;
  messages: StudioChatMessage[];
  onAppendToDocument: (markdown: string) => void;
  onAttachFiles: (files: FileList | null) => void;
  onComposerTextChange: (value: string) => void;
  onCopyMarkdown: (markdown: string) => void;
  onCreateNewDocument: (markdown: string) => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onReasoningEffortChange: (value: string) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => boolean | Promise<boolean>;
  onStreamOutputChange: (value: boolean) => void;
  onThinkingBudgetChange: (value: string) => void;
  onThinkingLevelChange: (value: string) => void;
  onToggleContext: (path: string) => void;
  onToggleWriteToCurrentDocument: () => void;
  providerOptions: StudioProviderOption[];
  selectConversation: (conversationId: string) => void;
  selectedContextPaths: string[];
  selectedCredentialApiDialect: string | null;
  selectedCredentialLabel: string | null;
  settings: Pick<
    StudioChatSettings,
    "modelName" | "provider" | "reasoningEffort" | "streamOutput" | "thinkingBudget" | "thinkingLevel"
  >;
  showWriteToCurrentDocument: boolean;
  skillModel: StudioChatSkillModel;
  visibleModelLabel: string;
  writeIntentNotice: string | null;
  writeTargetDisabledReason: string | null;
  isWriteToCurrentDocumentEnabled: boolean;
};

export function AiChatPanel({
  activeConversationId,
  attachments,
  availableContexts,
  canChat,
  layoutMode = "default",
  composerText,
  conversationSummaries,
  createConversation,
  credentialNotice,
  credentialSettingsHref,
  credentialState,
  currentDocumentPath,
  deleteConversation,
  isCredentialLoading,
  isResponding = false,
  messages,
  onAppendToDocument,
  onAttachFiles,
  onComposerTextChange,
  onCopyMarkdown,
  onCreateNewDocument,
  onModelNameChange,
  onProviderChange,
  onReasoningEffortChange,
  onRemoveAttachment,
  onSendMessage,
  onStreamOutputChange,
  onThinkingBudgetChange,
  onThinkingLevelChange,
  onToggleContext,
  onToggleWriteToCurrentDocument,
  providerOptions,
  selectConversation,
  selectedContextPaths,
  selectedCredentialApiDialect,
  selectedCredentialLabel,
  settings,
  showWriteToCurrentDocument,
  skillModel,
  visibleModelLabel,
  writeIntentNotice,
  writeTargetDisabledReason,
  isWriteToCurrentDocumentEnabled,
}: Readonly<AiChatPanelProps>) {
  const transcriptRef = useRef<HTMLDivElement>(null);
  const [activeHeaderPanel, setActiveHeaderPanel] = useState<"history" | "skill" | null>(null);
  const compactLayout = layoutMode !== "default";

  useEffect(() => {
    const node = transcriptRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  return (
    <aside className="chat-root">
      {/* 头部 */}
      <header className="chat-header">
        <div className={`chat-header__top ${compactLayout ? "chat-header__top--compact" : ""}`}>
          <div className="chat-header__title-wrap">
            <h2 className="chat-header__title">共创助手</h2>
            <span className={`chat-header__status ${resolveStatusToneClassName(credentialState)}`}>
              {resolveStudioStatusLabel({ canChat, credentialState })}
            </span>
          </div>
          {currentDocumentPath ? (
            <p className={`chat-header__doc ${compactLayout ? "chat-header__doc--compact" : ""}`}>
              当前文稿 · {currentDocumentPath}
            </p>
          ) : null}
        </div>
        <div className={`chat-header__controls ${compactLayout ? "chat-header__controls--compact" : ""}`}>
          <StudioChatSkillPanel
            layoutMode={layoutMode}
            disabled={isResponding}
            isOpen={activeHeaderPanel === "skill"}
            model={skillModel}
            onOpenChange={(open) => setActiveHeaderPanel((current) => (open ? "skill" : current === "skill" ? null : current))}
          />
          <StudioChatHistoryPanel
            activeConversationId={activeConversationId}
            layoutMode={layoutMode}
            conversations={conversationSummaries}
            disabled={isResponding}
            isOpen={activeHeaderPanel === "history"}
            onCreateConversation={createConversation}
            onDeleteConversation={deleteConversation}
            onOpenChange={(open) => setActiveHeaderPanel((current) => (open ? "history" : current === "history" ? null : current))}
            onSelectConversation={selectConversation}
          />
        </div>
      </header>

      {/* 消息区域 */}
      <div className="chat-transcript" ref={transcriptRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty__icon">✦</div>
            <p className="chat-empty__title">
              {canChat ? "把问题、片段，或者文件直接丢进来就行。" : "先接入一个可用模型，再开始共创。"}
            </p>
            <p className="chat-empty__desc">
              上下文、模型、文件都收进底部工具条，主舞台只留给对话和正文。
            </p>
          </div>
        ) : null}
        {messages.map((message) => (
          <StudioChatMessageBubble
            key={message.id}
            message={message}
            onAppendToDocument={onAppendToDocument}
            onCopyMarkdown={onCopyMarkdown}
            onCreateNewDocument={onCreateNewDocument}
          />
        ))}
        {isResponding ? (
          <div className="chat-typing">
            <span className="chat-typing__dot" />
            <span className="chat-typing__dot" />
            <span className="chat-typing__dot" />
          </div>
        ) : null}
      </div>

      {/* 底部输入区 */}
      <StudioChatComposer
        attachments={attachments}
        availableContexts={availableContexts}
        canChat={canChat}
        layoutMode={layoutMode}
        composerText={composerText}
        credentialNotice={credentialNotice}
        credentialSettingsHref={credentialSettingsHref}
        isCredentialLoading={isCredentialLoading}
        isResponding={isResponding}
        modelButtonLabel={visibleModelLabel}
        onAttachFiles={onAttachFiles}
        onComposerTextChange={onComposerTextChange}
        onModelNameChange={onModelNameChange}
        onProviderChange={onProviderChange}
        onReasoningEffortChange={onReasoningEffortChange}
        onRemoveAttachment={onRemoveAttachment}
        onSendMessage={onSendMessage}
        onStreamOutputChange={onStreamOutputChange}
        onThinkingBudgetChange={onThinkingBudgetChange}
        onThinkingLevelChange={onThinkingLevelChange}
        onToggleContext={onToggleContext}
        onToggleWriteToCurrentDocument={onToggleWriteToCurrentDocument}
        providerOptions={providerOptions}
        selectedContextPaths={selectedContextPaths}
        selectedCredentialApiDialect={selectedCredentialApiDialect}
        selectedCredentialLabel={selectedCredentialLabel}
        settings={settings}
        showWriteToCurrentDocument={showWriteToCurrentDocument}
        writeIntentNotice={writeIntentNotice}
        writeTargetDisabledReason={writeTargetDisabledReason}
        isWriteToCurrentDocumentEnabled={isWriteToCurrentDocumentEnabled}
      />
    </aside>
  );
}

function resolveStatusToneClassName(credentialState: AiChatPanelProps["credentialState"]) {
  const tone = resolveStudioStatusTone(credentialState);
  if (tone === "danger") {
    return "chat-status--danger";
  }
  if (tone === "muted") {
    return "chat-status--muted";
  }
  return "chat-status--ready";
}
