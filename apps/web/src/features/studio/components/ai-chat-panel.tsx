"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Checkbox } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

import type { StudioChatAttachmentMeta } from "./studio-chat-attachment-support";
import { StudioChatComposer } from "./studio-chat-composer";
import { StudioChatMessageBubble } from "./studio-chat-message-bubble";
import type {
  StudioChatMessage,
  StudioChatSettings,
  StudioProviderOption,
} from "./studio-chat-support";
import { resolveStudioStatusLabel, resolveStudioStatusTone } from "./studio-chat-ui-support";
import styles from "./ai-chat-panel.module.css";

type AiChatPanelProps = {
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
  credentialNotice: string | null;
  credentialSettingsHref: string;
  credentialState: "empty" | "error" | "loading" | "ready";
  currentDocumentPath: string | null;
  isCredentialLoading: boolean;
  isResponding?: boolean;
  messages: StudioChatMessage[];
  onAppendToDocument: (markdown: string) => void;
  onAttachFiles: (files: FileList | null) => void;
  onCopyMarkdown: (markdown: string) => void;
  onCreateNewDocument: (markdown: string) => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => void;
  onToggleContext: (path: string) => void;
  providerOptions: StudioProviderOption[];
  selectedContextPaths: string[];
  selectedCredentialLabel: string | null;
  settings: Pick<StudioChatSettings, "modelName" | "provider">;
  visibleModelLabel: string;
};

export function AiChatPanel({
  attachments,
  availableContexts,
  canChat,
  credentialNotice,
  credentialSettingsHref,
  credentialState,
  currentDocumentPath,
  isCredentialLoading,
  isResponding = false,
  messages,
  onAppendToDocument,
  onAttachFiles,
  onCopyMarkdown,
  onCreateNewDocument,
  onModelNameChange,
  onProviderChange,
  onRemoveAttachment,
  onSendMessage,
  onToggleContext,
  providerOptions,
  selectedContextPaths,
  selectedCredentialLabel,
  settings,
  visibleModelLabel,
}: Readonly<AiChatPanelProps>) {
  const [showContextSelector, setShowContextSelector] = useState(false);
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
    <aside className={styles.panel}>
      <header className={styles.header}>
        <div className={styles.headerInfo}>
          <div className={styles.headerRow}>
            <h2 className={styles.title}>共创助手</h2>
            <span className={`${styles.statusPill} ${resolveStatusToneClassName(credentialState)}`}>
              {resolveStudioStatusLabel({ canChat, credentialState })}
            </span>
          </div>
          <p className={styles.subtitle}>围绕当前文稿推进，模型、上下文和文件都收进底部工具条。</p>
          {currentDocumentPath ? (
            <p className={styles.currentDocument}>当前文稿 · {currentDocumentPath}</p>
          ) : null}
        </div>
      </header>

      {showContextSelector ? (
        <section className={styles.contextSelector}>
          <p className={styles.contextLabel}>附加文档上下文</p>
          <div className={styles.contextList}>
            {flatContexts.filter((node) => node.type === "file").map((node) => (
              <label className={styles.contextItem} key={node.id}>
                <Checkbox checked={selectedContextPaths.includes(node.path)} onChange={() => onToggleContext(node.path)} />
                <span className={styles.contextPath}>{node.path}</span>
              </label>
            ))}
          </div>
        </section>
      ) : null}

      <div className={styles.transcript} ref={transcriptRef}>
        {messages.length === 0 ? (
          <div className={styles.emptyChat}>
            <div className={styles.emptyIcon}>✦</div>
            <p className={styles.emptyText}>{canChat ? "把问题、片段，或者文件直接丢进来就行。" : "先接入一个可用模型，再开始共创。"}</p>
            <p className={styles.emptyHint}>上下文、模型、文件都收进底部工具条，主舞台只留给对话和正文。</p>
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
          <div className={styles.typingIndicator}>
            <span className={styles.typingDot} />
            <span className={styles.typingDot} />
            <span className={styles.typingDot} />
          </div>
        ) : null}
      </div>

      <StudioChatComposer
        attachments={attachments}
        canChat={canChat}
        credentialNotice={credentialNotice}
        credentialSettingsHref={credentialSettingsHref}
        isCredentialLoading={isCredentialLoading}
        isContextSelectorOpen={showContextSelector}
        isResponding={isResponding}
        modelButtonLabel={visibleModelLabel}
        onAttachFiles={onAttachFiles}
        onModelNameChange={onModelNameChange}
        onProviderChange={onProviderChange}
        onRemoveAttachment={onRemoveAttachment}
        onSendMessage={onSendMessage}
        onToggleContextSelector={() => setShowContextSelector((current) => !current)}
        providerOptions={providerOptions}
        selectedContextCount={selectedContextPaths.length}
        selectedCredentialLabel={selectedCredentialLabel}
        settings={settings}
      />
    </aside>
  );
}

function flattenStudioContexts(nodes: DocumentTreeNode[]) {
  return nodes.flatMap((node) => (node.children ? [node, ...node.children] : [node]));
}

function resolveStatusToneClassName(
  credentialState: AiChatPanelProps["credentialState"],
) {
  const tone = resolveStudioStatusTone(credentialState);
  if (tone === "danger") {
    return styles.statusPillDanger;
  }
  if (tone === "muted") {
    return styles.statusPillMuted;
  }
  return styles.statusPillReady;
}
