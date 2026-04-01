"use client";

import { useState } from "react";
import { Button } from "@arco-design/web-react";

import { formatStudioChatAttachmentSize } from "./studio-chat-attachment-support";
import type { StudioChatMessage } from "./studio-chat-support";

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
      className={`relative mb-3.5 px-4 py-3.5 rounded-[22px] text-sm leading-relaxed animate-[fadeIn_0.3s_ease_forwards] ${isAssistant ? "mr-8 bg-[rgba(90,122,107,0.08)]" : "ml-8 bg-[rgba(255,255,255,0.72)]"} ${message.status === "error" ? "shadow-[inset_0_0_0_1px_rgba(178,65,46,0.12)]" : ""}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <p className="m-0 mb-1.5 text-[0.66rem] font-semibold tracking-widest uppercase text-[var(--text-tertiary)]">{isAssistant ? "助手" : "你"}</p>
      <div className="text-[var(--text-primary)] text-sm leading-relaxed">
        {isAssistant ? <MarkdownContent content={message.content} /> : <p className="m-0 whitespace-pre-wrap break-words">{message.content}</p>}
      </div>
      {message.attachments?.length ? (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {message.attachments.map((attachment) => (
            <span className="inline-flex items-center min-h-7 px-2.5 py-1 rounded-full bg-[rgba(61,61,61,0.06)] text-[var(--text-secondary)] text-[0.72rem] leading-relaxed" key={attachment.id}>
              {attachment.name} · {formatStudioChatAttachmentSize(attachment.size)}
            </span>
          ))}
        </div>
      ) : null}
      {isAssistant && message.status !== "pending" && showActions ? (
        <div className="flex flex-wrap gap-1.5 mt-3">
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
      className="text-sm leading-relaxed [&_h1]:my-3 [&_h1]:mb-1.5 [&_h2]:my-3 [&_h2]:mb-1.5 [&_h3]:my-3 [&_h3]:mb-1.5 [&_p]:my-2 [&_blockquote]:my-2 [&_blockquote]:py-0.5 [&_blockquote]:pl-3 [&_blockquote]:border-l-2 [&_blockquote]:border-[var(--accent-primary)] [&_blockquote]:text-[var(--text-secondary)] [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded-[var(--radius-xs)] [&_code]:bg-[rgba(135,131,120,0.15)] [&_code]:text-[#9b3f2e] [&_code]:font-mono [&_code]:text-[0.88em]"
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
    `<pre class="my-3 px-3.5 py-3 rounded-2xl bg-[rgba(61,61,61,0.05)] text-[var(--text-primary)] font-mono text-xs leading-relaxed overflow-x-auto" data-lang="${lang}"><code>${code.trim()}</code></pre>`);

  return html;
}
