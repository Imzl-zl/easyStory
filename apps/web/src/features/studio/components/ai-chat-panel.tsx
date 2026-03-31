"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button, Input, Checkbox } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";
import styles from "./ai-chat-panel.module.css";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  rawMarkdown: string;
  status?: "pending" | "error";
  timestamp: Date;
};

type AiChatPanelProps = {
  currentDocumentPath: string | null;
  currentDocumentContent: string;
  availableContexts: DocumentTreeNode[];
  selectedContextPaths: string[];
  onToggleContext: (path: string) => void;
  onSendMessage: (message: string, contextPaths: string[]) => void;
  messages: ChatMessage[];
  isResponding?: boolean;
  onCopyMarkdown: (markdown: string) => void;
  onAppendToDocument: (markdown: string) => void;
  onCreateNewDocument: (markdown: string) => void;
};

export function AiChatPanel({
  currentDocumentPath,
  availableContexts,
  selectedContextPaths,
  onToggleContext,
  onSendMessage,
  messages,
  isResponding = false,
  onCopyMarkdown,
  onAppendToDocument,
  onCreateNewDocument,
}: Readonly<AiChatPanelProps>) {
  const [inputText, setInputText] = useState("");
  const [showContextSelector, setShowContextSelector] = useState(false);
  const transcriptRef = useRef<HTMLDivElement>(null);

  const handleSubmit = useCallback(() => {
    if (!inputText.trim() || isResponding) {
      return;
    }
    onSendMessage(inputText.trim(), selectedContextPaths);
    setInputText("");
  }, [inputText, isResponding, onSendMessage, selectedContextPaths]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  useEffect(() => {
    const node = transcriptRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [messages]);

  const flatContexts = availableContexts.flatMap((node) => {
    if (node.children) {
      return [node, ...node.children];
    }
    return [node];
  });

  return (
    <aside className={styles.panel}>
      <header className={styles.header}>
        <div className={styles.headerInfo}>
          <div className={styles.headerRow}>
            <h2 className={styles.title}>共创助手</h2>
            <span className={styles.statusPill}>接入中</span>
          </div>
          <p className={styles.subtitle}>当前先保留上下文选择、片段采纳和写作协作入口，不伪装为正式生成能力。</p>
        </div>
        <Button
          size="small"
          shape="round"
          type="secondary"
          onClick={() => setShowContextSelector(!showContextSelector)}
        >
          {showContextSelector ? "收起上下文" : "选择上下文"}
        </Button>
      </header>

      {currentDocumentPath ? (
        <div className={styles.currentContext}>当前文稿 · {currentDocumentPath}</div>
      ) : null}

      {showContextSelector ? (
        <div className={styles.contextSelector}>
          <p className={styles.contextLabel}>附加文档上下文</p>
          <div className={styles.contextList}>
            {flatContexts.filter((n) => n.type === "file").map((node) => (
              <label key={node.id} className={styles.contextItem}>
                <Checkbox
                  checked={selectedContextPaths.includes(node.path)}
                  onChange={() => onToggleContext(node.path)}
                />
                <span className={styles.contextPath}>{node.path}</span>
              </label>
            ))}
          </div>
        </div>
      ) : null}

      <div className={styles.transcript} ref={transcriptRef}>
        {messages.length === 0 ? (
          <div className={styles.emptyChat}>
            <div className={styles.emptyIcon}>✦</div>
            <p className={styles.emptyText}>先把问题写清楚，再让助手介入。</p>
            <p className={styles.emptyHint}>可以先勾选总大纲、人物设定或章节草稿，让右侧协作更贴近当前文稿。</p>
          </div>
        ) : null}
        {messages.map((message) => (
          <ChatMessageBubble
            key={message.id}
            message={message}
            onCopyMarkdown={onCopyMarkdown}
            onAppendToDocument={onAppendToDocument}
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

      <footer className={styles.composer}>
        <div className={styles.composerInner}>
          <Input.TextArea
            autoSize={{ minRows: 2, maxRows: 5 }}
            placeholder="例如：根据当前文档整理成更清晰的大纲"
            value={inputText}
            onChange={setInputText}
            onKeyDown={handleKeyDown}
            className={styles.composerInput}
          />
          <div className={styles.composerActions}>
            <span className={styles.hint}>{inputText.length} 字 · Enter 发送 · 当前为接入阶段</span>
            <Button
              type="primary"
              shape="round"
              size="small"
              loading={isResponding}
              disabled={!inputText.trim()}
              onClick={handleSubmit}
            >
              发送
            </Button>
          </div>
        </div>
      </footer>
    </aside>
  );
}

function ChatMessageBubble({
  message,
  onCopyMarkdown,
  onAppendToDocument,
  onCreateNewDocument,
}: {
  message: ChatMessage;
  onCopyMarkdown: (markdown: string) => void;
  onAppendToDocument: (markdown: string) => void;
  onCreateNewDocument: (markdown: string) => void;
}) {
  const isAssistant = message.role === "assistant";
  const [showActions, setShowActions] = useState(false);

  return (
    <article
      className={`${styles.message} ${isAssistant ? styles.messageAssistant : styles.messageUser}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <p className={styles.messageRole}>{isAssistant ? "助手" : "你"}</p>
      <div className={styles.messageContent}>
        {isAssistant ? (
          <MarkdownContent content={message.content} />
        ) : (
          <p className={styles.plainText}>{message.content}</p>
        )}
      </div>
      {isAssistant && showActions ? (
        <div className={styles.messageActions}>
          <Button size="mini" shape="round" type="secondary" onClick={() => onCopyMarkdown(message.rawMarkdown || message.content)}>
            复制 Markdown
          </Button>
          <Button size="mini" shape="round" type="secondary" onClick={() => onAppendToDocument(message.rawMarkdown || message.content)}>
            追加到文档
          </Button>
          <Button size="mini" shape="round" type="secondary" onClick={() => onCreateNewDocument(message.rawMarkdown || message.content)}>
            新建文档
          </Button>
        </div>
      ) : null}
    </article>
  );
}

function MarkdownContent({ content }: { content: string }) {
  const renderMarkdown = (text: string): string => {
    let html = text
      .replace(/^### (.*$)/gim, "<h3>$1</h3>")
      .replace(/^## (.*$)/gim, "<h2>$1</h2>")
      .replace(/^# (.*$)/gim, "<h1>$1</h1>")
      .replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>")
      .replace(/\*\*(.*)\*\*/gim, "<strong>$1</strong>")
      .replace(/\*(.*)\*/gim, "<em>$1</em>")
      .replace(/`([^`]+)`/gim, "<code>$1</code>")
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/gim, '<img alt="$1" src="$2" />')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/^\- (.*$)/gim, "<li>$1</li>")
      .replace(/^\d+\. (.*$)/gim, "<li>$1</li>")
      .replace(/\n/gim, "<br>");

    html = html.replace(/```(\w*)\n([\s\S]*?)```/gim, (_, lang, code) => {
      return `<pre class="${styles.codeBlock}" data-lang="${lang}"><code>${code.trim()}</code></pre>`;
    });

    return html;
  };

  return (
    <div
      className={styles.markdownContent}
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}
