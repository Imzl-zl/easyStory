"use client";

import { useEffect, useMemo, useRef } from "react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

import type { StudioChatAttachmentMeta } from "./studio-chat-attachment-support";
import { StudioChatHistoryPanel } from "./studio-chat-history-panel";
import { StudioChatComposer } from "./studio-chat-composer";
import { StudioChatMessageBubble } from "./studio-chat-message-bubble";
import type { StudioConversationSummary } from "./studio-chat-store-support";
import type {
  StudioChatMessage,
  StudioChatSettings,
  StudioProviderOption,
} from "./studio-chat-support";
import { resolveStudioStatusLabel, resolveStudioStatusTone } from "./studio-chat-ui-support";

type AiChatPanelProps = {
  activeConversationId: string;
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
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
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => void;
  onStreamOutputChange: (value: boolean) => void;
  onToggleContext: (path: string) => void;
  providerOptions: StudioProviderOption[];
  selectConversation: (conversationId: string) => void;
  selectedContextPaths: string[];
  selectedCredentialLabel: string | null;
  settings: Pick<StudioChatSettings, "modelName" | "provider" | "streamOutput">;
  visibleModelLabel: string;
};

export function AiChatPanel({
  activeConversationId,
  attachments,
  availableContexts,
  canChat,
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
  onRemoveAttachment,
  onSendMessage,
  onStreamOutputChange,
  onToggleContext,
  providerOptions,
  selectConversation,
  selectedContextPaths,
  selectedCredentialLabel,
  settings,
  visibleModelLabel,
}: Readonly<AiChatPanelProps>) {
  const transcriptRef = useRef<HTMLDivElement>(null);

  const flatContexts = useMemo(
    () => flattenStudioContexts(availableContexts),
    [availableContexts],
  );

  useEffect(() => {
    const node = transcriptRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  return (
    <aside className="relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-gradient-to-b from-[#fefdfb] to-[#f9f7f3]">
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%221.2%22_numOctaves%3D%223%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />
      
      <header className="relative z-10 shrink-0 px-5 pt-5 pb-4 bg-gradient-to-b from-white/95 to-[rgba(254,253,251,0.8)] border-b border-[rgba(44,36,22,0.06)]">
        <div className="absolute bottom-0 left-4 right-4 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)] to-transparent opacity-20" />
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2.5">
            <h2 className="m-0 font-serif text-lg font-bold tracking-tight text-[var(--text-primary)]">共创助手</h2>
            <span className={`inline-flex items-center h-[22px] px-2 rounded text-[0.65rem] font-semibold tracking-widest uppercase transition-all ${resolveStatusToneClassName(credentialState)}`}>
              {resolveStudioStatusLabel({ canChat, credentialState })}
            </span>
          </div>
          <p className="m-0 text-xs leading-relaxed text-[var(--text-muted)]">围绕当前文稿推进，模型、上下文和文件都收进底部工具条。</p>
          {currentDocumentPath ? (
            <p className="m-0 mt-1 max-w-full break-all rounded-md bg-[rgba(107,143,113,0.08)] px-2.5 py-1.5 text-xs leading-relaxed text-[var(--text-secondary)] w-fit">
              当前文稿 · {currentDocumentPath}
            </p>
          ) : null}
          <StudioChatHistoryPanel
            activeConversationId={activeConversationId}
            conversations={conversationSummaries}
            disabled={isResponding}
            onCreateConversation={createConversation}
            onDeleteConversation={deleteConversation}
            onSelectConversation={selectConversation}
          />
        </div>
      </header>

      <div className="relative z-10 flex-1 min-h-0 min-w-0 overflow-x-hidden overflow-y-auto px-5 py-2 scrollbar-thin [&::-webkit-scrollbar]:w-[5px] [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-[3px] [&::-webkit-scrollbar-thumb]:bg-[rgba(44,36,22,0.12)]" ref={transcriptRef}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-[200px] h-full p-8 text-center">
            <div className="flex items-center justify-center w-12 h-12 mb-3 rounded-[10px] bg-gradient-to-br from-[var(--accent-primary)] to-[#5a7a60] text-white text-base shadow-[0_3px_10px_rgba(107,143,113,0.25)]">
              ✦
            </div>
            <p className="m-0 mb-1 text-sm font-semibold text-[var(--text-primary)]">
              {canChat ? "把问题、片段，或者文件直接丢进来就行。" : "先接入一个可用模型，再开始共创。"}
            </p>
            <p className="m-0 max-w-[14rem] text-xs leading-relaxed text-[var(--text-muted)]">
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
            <span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-primary)] opacity-40 animate-[typingPulse_1.4s_ease-in-out_infinite]" />
            <span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-primary)] opacity-40 animate-[typingPulse_1.4s_ease-in-out_infinite_0.15s]" />
            <span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-primary)] opacity-40 animate-[typingPulse_1.4s_ease-in-out_infinite_0.3s]" />
          </div>
        ) : null}
      </div>

      <StudioChatComposer
        attachments={attachments}
        availableContexts={flatContexts}
        canChat={canChat}
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
        onRemoveAttachment={onRemoveAttachment}
        onSendMessage={onSendMessage}
        onStreamOutputChange={onStreamOutputChange}
        onToggleContext={onToggleContext}
        providerOptions={providerOptions}
        selectedContextPaths={selectedContextPaths}
        selectedCredentialLabel={selectedCredentialLabel}
        settings={settings}
      />
    </aside>
  );
}

function flattenStudioContexts(nodes: DocumentTreeNode[]) {
  return nodes.flatMap((node) => (node.children ? [node, ...node.children] : [node]));
}

function resolveStatusToneClassName(credentialState: AiChatPanelProps["credentialState"]) {
  const tone = resolveStudioStatusTone(credentialState);
  if (tone === "danger") {
    return "bg-gradient-to-br from-[#b2412e] to-[#8b4335] text-white shadow-[0_2px_6px_rgba(178,65,46,0.25)]";
  }
  if (tone === "muted") {
    return "bg-[rgba(44,36,22,0.08)] text-[var(--text-muted)]";
  }
  return "bg-gradient-to-br from-[var(--accent-primary)] to-[#5a7a60] text-white shadow-[0_2px_6px_rgba(107,143,113,0.25)]";
}
