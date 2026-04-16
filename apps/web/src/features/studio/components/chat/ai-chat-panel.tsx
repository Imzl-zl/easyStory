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
    <aside className="relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-gradient-to-b from-surface to-muted">
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%221.2%22_numOctaves%3D%223%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />
      
      <header className="relative z-[180] shrink-0 px-4 pt-4 pb-3 bg-gradient-to-b from-elevated/95 to-glass border-b border-line-soft">
        <div className="absolute bottom-0 left-4 right-4 h-px bg-gradient-to-r from-transparent via-accent-primary to-transparent opacity-20" />
        <div className={`flex gap-3 ${compactLayout ? "flex-col items-start" : "items-start justify-between"}`}>
          <div className="flex min-w-0 items-center gap-2.5">
            <h2 className="m-0 font-serif text-[1.05rem] font-bold tracking-tight text-text-primary">共创助手</h2>
            <span className={`inline-flex items-center h-[22px] px-2 rounded text-[0.65rem] font-semibold tracking-widest uppercase transition-all ${resolveStatusToneClassName(credentialState)}`}>
              {resolveStudioStatusLabel({ canChat, credentialState })}
            </span>
          </div>
          {currentDocumentPath ? (
            <p className={`m-0 break-all rounded-md bg-accent-soft px-2.5 py-1 text-[11px] leading-5 text-text-secondary ${compactLayout ? "w-full max-w-none" : "max-w-full lg:max-w-[16rem]"}`}>
              当前文稿 · {currentDocumentPath}
            </p>
          ) : null}
        </div>
        <div className={`relative z-[180] mt-2 flex w-full min-w-0 gap-2 ${compactLayout ? "flex-col items-stretch" : "items-center"}`}>
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

      <div className="relative z-10 flex-1 min-h-0 min-w-0 overflow-x-hidden overflow-y-auto px-4 py-3 scrollbar-thin [&::-webkit-scrollbar]:w-[5px] [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-[3px] [&::-webkit-scrollbar-thumb]:bg-line-strong" ref={transcriptRef}>
        {messages.length === 0 ? (
          <div className="flex h-full min-h-[160px] flex-col items-center justify-center p-6 text-center">
            <div className="flex items-center justify-center w-12 h-12 mb-3 rounded-[10px] bg-gradient-to-br from-accent-primary to-accent-primary text-white text-base shadow-md">
              ✦
            </div>
            <p className="m-0 mb-1 text-sm font-semibold text-text-primary">
              {canChat ? "把问题、片段，或者文件直接丢进来就行。" : "先接入一个可用模型，再开始共创。"}
            </p>
            <p className="m-0 max-w-[14rem] text-xs leading-relaxed text-text-tertiary">
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
          <div className="flex items-center gap-1 px-3 py-1.5 mt-1">
            <span className="w-[5px] h-[5px] rounded-full bg-accent-primary opacity-40 animate-[typingPulse_1.4s_ease-in-out_infinite]" />
            <span className="w-[5px] h-[5px] rounded-full bg-accent-primary opacity-40 animate-[typingPulse_1.4s_ease-in-out_infinite_0.15s]" />
            <span className="w-[5px] h-[5px] rounded-full bg-accent-primary opacity-40 animate-[typingPulse_1.4s_ease-in-out_infinite_0.3s]" />
          </div>
        ) : null}
      </div>

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
    return "bg-gradient-to-br from-accent-danger to-accent-danger/80 text-white shadow-md";
  }
  if (tone === "muted") {
    return "bg-surface-hover text-text-tertiary";
  }
  return "bg-gradient-to-br from-accent-primary to-accent-primary text-white shadow-sm";
}
