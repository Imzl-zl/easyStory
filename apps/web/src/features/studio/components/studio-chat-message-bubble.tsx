"use client";

import { useState } from "react";
import { Button } from "@arco-design/web-react";

import { matchAssistantMarkdownDocument } from "@/features/shared/assistant/assistant-markdown-document-support";

import { formatStudioChatAttachmentSize } from "./studio-chat-attachment-support";
import {
  resolveStudioAssistantMessageActionState,
  type StudioChatMessage,
  type StudioChatToolProgressTone,
} from "./studio-chat-support";

type StudioChatMessageBubbleProps = {
  message: StudioChatMessage;
  onAppendToDocument: (markdown: string) => void;
  onCopyMarkdown: (markdown: string) => void;
  onCreateNewDocument: (markdown: string) => void;
};

const MESSAGE_BUBBLE_BASE_CLASS =
  "relative mb-3.5 w-full min-w-0 max-w-[calc(100%-2rem)] overflow-hidden rounded-[22px] px-4 py-3.5 text-sm leading-relaxed animate-[fadeIn_0.3s_ease_forwards]";
const ASSISTANT_MESSAGE_CLASS = "mr-8 bg-[rgba(90,122,107,0.08)]";
const USER_MESSAGE_CLASS = "ml-8 bg-[rgba(255,255,255,0.72)]";
const MESSAGE_CONTENT_CLASS = "min-w-0 max-w-full overflow-hidden text-[var(--text-primary)] text-sm leading-relaxed";
const MARKDOWN_CONTENT_CLASS =
  "min-w-0 max-w-full overflow-hidden break-words [overflow-wrap:anywhere] text-sm leading-relaxed [&_a]:break-all [&_a]:text-[var(--accent-primary)] [&_a]:underline [&_a]:underline-offset-2 [&_blockquote]:my-2 [&_blockquote]:border-l-2 [&_blockquote]:border-[var(--accent-primary)] [&_blockquote]:py-0.5 [&_blockquote]:pl-3 [&_blockquote]:text-[var(--text-secondary)] [&_blockquote]:break-words [&_blockquote]:[overflow-wrap:anywhere] [&_code]:break-words [&_code]:rounded-[var(--radius-xs)] [&_code]:bg-[rgba(135,131,120,0.15)] [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.88em] [&_code]:text-[#9b3f2e] [&_h1]:my-3 [&_h1]:mb-1.5 [&_h2]:my-3 [&_h2]:mb-1.5 [&_h3]:my-3 [&_h3]:mb-1.5 [&_img]:h-auto [&_img]:max-w-full [&_li]:break-words [&_li]:[overflow-wrap:anywhere] [&_p]:my-2 [&_p]:break-words [&_p]:[overflow-wrap:anywhere] [&_pre]:my-3 [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre_code]:break-normal [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-inherit";
const ATTACHMENT_PILL_CLASS =
  "inline-flex max-w-full items-center min-h-7 break-all px-2.5 py-1 rounded-full bg-[rgba(61,61,61,0.06)] text-[var(--text-secondary)] text-[0.72rem] leading-relaxed";

export function StudioChatMessageBubble({
  message,
  onAppendToDocument,
  onCopyMarkdown,
  onCreateNewDocument,
}: Readonly<StudioChatMessageBubbleProps>) {
  const [showActions, setShowActions] = useState(false);
  const isAssistant = message.role === "assistant";
  const actionState = resolveStudioAssistantMessageActionState(message);
  const documentMatch = isAssistant && actionState.documentMatchSource
    ? matchAssistantMarkdownDocument(actionState.documentMatchSource)
    : null;
  const actionContent = documentMatch?.body ?? actionState.actionContent;

  return (
    <article
      className={`${MESSAGE_BUBBLE_BASE_CLASS} ${isAssistant ? ASSISTANT_MESSAGE_CLASS : USER_MESSAGE_CLASS} ${message.status === "error" ? "shadow-[inset_0_0_0_1px_rgba(178,65,46,0.12)]" : ""}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <p className="m-0 mb-1.5 text-[0.66rem] font-semibold tracking-widest uppercase text-[var(--text-tertiary)]">{isAssistant ? "助手" : "你"}</p>
      {isAssistant && message.toolProgress?.length ? (
        <div className="mb-2.5 flex flex-col gap-1.5">
          {message.toolProgress.map((item) => (
            <ToolProgressCard
              key={item.toolCallId}
              detail={item.detail}
              label={item.label}
              statusLabel={item.statusLabel}
              tone={item.tone}
            />
          ))}
        </div>
      ) : null}
      <div className={MESSAGE_CONTENT_CLASS}>
        {isAssistant ? (
          <MarkdownContent
            content={message.content}
            documentMatch={documentMatch}
            onCopyMarkdown={onCopyMarkdown}
          />
        ) : <p className="m-0 whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{message.content}</p>}
      </div>
      {message.attachments?.length ? (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {message.attachments.map((attachment) => (
            <span className={ATTACHMENT_PILL_CLASS} key={attachment.id}>
              {attachment.name} · {formatStudioChatAttachmentSize(attachment.size)}
            </span>
          ))}
        </div>
      ) : null}
      {isAssistant && actionState.showCopyAction && showActions ? (
        <div className="flex flex-wrap gap-1.5 mt-3">
          <Button size="mini" shape="round" type="secondary" onClick={() => onCopyMarkdown(actionContent)}>
            {actionState.copyLabel}
          </Button>
          {actionState.showDocumentActions ? (
            <Button size="mini" shape="round" type="secondary" onClick={() => onAppendToDocument(actionContent)}>
              追加到文档
            </Button>
          ) : null}
          {actionState.showDocumentActions ? (
            <Button size="mini" shape="round" type="secondary" onClick={() => onCreateNewDocument(actionContent)}>
              新建文档
            </Button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function ToolProgressCard({
  detail,
  label,
  statusLabel,
  tone,
}: {
  detail?: string;
  label: string;
  statusLabel: string;
  tone: StudioChatToolProgressTone;
}) {
  const toneClasses = resolveToolProgressToneClasses(tone);
  return (
    <section className={`rounded-[16px] border px-3 py-2 ${toneClasses.card}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="m-0 text-[12px] font-medium text-[var(--text-primary)]">{label}</p>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-[0.08em] uppercase ${toneClasses.badge}`}>
          {statusLabel}
        </span>
      </div>
      {detail ? (
        <p className="m-0 mt-1 text-[11px] leading-5 text-[var(--text-secondary)] break-words [overflow-wrap:anywhere]">{detail}</p>
      ) : null}
    </section>
  );
}

function MarkdownContent({
  content,
  documentMatch,
  onCopyMarkdown,
}: {
  content: string;
  documentMatch: ReturnType<typeof matchAssistantMarkdownDocument>;
  onCopyMarkdown: (markdown: string) => void;
}) {
  if (documentMatch) {
    return (
      <div className="space-y-2">
        {documentMatch.leadingText ? (
          <MarkdownHtmlContent content={documentMatch.leadingText} />
        ) : null}
        <section className="my-1 overflow-hidden rounded-[18px] border border-[rgba(44,36,22,0.1)] bg-[rgba(58,45,29,0.03)]">
          <header className="flex items-center justify-between gap-3 border-b border-[rgba(44,36,22,0.08)] bg-[rgba(255,255,255,0.72)] px-3 py-2">
            <div className="min-w-0">
              <p className="m-0 text-[11px] font-semibold tracking-[0.12em] uppercase text-[var(--text-secondary)]">Markdown 文档</p>
              <p className="m-0 text-[11px] leading-5 text-[var(--text-muted)]">已自动识别为整段文档，支持直接复制。</p>
            </div>
            <button
              className="shrink-0 rounded-full border border-[rgba(44,36,22,0.08)] bg-white px-2.5 py-1 text-[11px] font-medium text-[var(--text-secondary)] transition hover:bg-[rgba(255,255,255,0.92)]"
              type="button"
              onClick={() => onCopyMarkdown(documentMatch.body)}
            >
              复制
            </button>
          </header>
          <pre className="m-0 max-w-full overflow-x-auto whitespace-pre-wrap break-words px-3.5 py-3 text-[12px] leading-6 text-[var(--text-primary)] [overflow-wrap:anywhere]">
            <code>{documentMatch.body}</code>
          </pre>
        </section>
        {documentMatch.trailingText ? (
          <MarkdownHtmlContent content={documentMatch.trailingText} />
        ) : null}
      </div>
    );
  }
  return <MarkdownHtmlContent content={content} />;
}

function MarkdownHtmlContent({ content }: { content: string }) {
  return (
    <div
      className={MARKDOWN_CONTENT_CLASS}
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
    `<pre class="my-3 max-w-full overflow-x-auto rounded-2xl bg-[rgba(61,61,61,0.05)] px-3.5 py-3 text-[var(--text-primary)] font-mono text-xs leading-relaxed" data-lang="${lang}"><code>${code.trim()}</code></pre>`);

  return html;
}

function resolveToolProgressToneClasses(tone: StudioChatToolProgressTone) {
  switch (tone) {
    case "danger":
      return {
        badge: "bg-[rgba(178,65,46,0.12)] text-[#8b4335]",
        card: "border-[rgba(178,65,46,0.16)] bg-[rgba(178,65,46,0.04)]",
      };
    case "muted":
      return {
        badge: "bg-[rgba(61,61,61,0.08)] text-[var(--text-secondary)]",
        card: "border-[rgba(44,36,22,0.08)] bg-[rgba(255,255,255,0.46)]",
      };
    case "success":
      return {
        badge: "bg-[rgba(107,143,113,0.14)] text-[#52705a]",
        card: "border-[rgba(107,143,113,0.14)] bg-[rgba(255,255,255,0.52)]",
      };
    default:
      return {
        badge: "bg-[rgba(107,143,113,0.14)] text-[#52705a]",
        card: "border-[rgba(107,143,113,0.16)] bg-[rgba(107,143,113,0.06)]",
      };
  }
}
