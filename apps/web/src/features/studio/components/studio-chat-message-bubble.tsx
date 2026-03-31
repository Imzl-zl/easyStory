"use client";

import { useState } from "react";
import { Button } from "@arco-design/web-react";

import { formatStudioChatAttachmentSize } from "./studio-chat-attachment-support";
import type { StudioChatMessage } from "./studio-chat-support";
import styles from "./studio-chat-message-bubble.module.css";

type StudioChatMessageBubbleProps = {
  message: StudioChatMessage;
  onAppendToDocument: (markdown: string) => void;
  onCopyMarkdown: (markdown: string) => void;
  onCreateNewDocument: (markdown: string) => void;
};

export function StudioChatMessageBubble({
  message,
  onAppendToDocument,
  onCopyMarkdown,
  onCreateNewDocument,
}: Readonly<StudioChatMessageBubbleProps>) {
  const [showActions, setShowActions] = useState(false);
  const isAssistant = message.role === "assistant";

  return (
    <article
      className={`${styles.message} ${isAssistant ? styles.messageAssistant : styles.messageUser} ${message.status === "error" ? styles.messageError : ""}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <p className={styles.messageRole}>{isAssistant ? "助手" : "你"}</p>
      <div className={styles.messageContent}>
        {isAssistant ? <MarkdownContent content={message.content} /> : <p className={styles.plainText}>{message.content}</p>}
      </div>
      {message.attachments?.length ? (
        <div className={styles.attachmentList}>
          {message.attachments.map((attachment) => (
            <span className={styles.attachmentChip} key={attachment.id}>
              {attachment.name} · {formatStudioChatAttachmentSize(attachment.size)}
            </span>
          ))}
        </div>
      ) : null}
      {isAssistant && message.status !== "pending" && showActions ? (
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
  return (
    <div
      className={styles.markdownContent}
      dangerouslySetInnerHTML={{ __html: renderStudioMarkdown(content) }}
    />
  );
}

function renderStudioMarkdown(text: string) {
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

  html = html.replace(/```(\w*)\n([\s\S]*?)```/gim, (_, lang, code) =>
    `<pre class="${styles.codeBlock}" data-lang="${lang}"><code>${code.trim()}</code></pre>`);

  return html;
}
