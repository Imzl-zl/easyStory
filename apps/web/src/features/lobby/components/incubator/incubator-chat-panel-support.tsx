"use client";

import Link from "next/link";

import { showAppNotice } from "@/components/ui/app-notice";
import { matchAssistantMarkdownDocument } from "@/features/shared/assistant/assistant-markdown-document-support";
import type { IncubatorCredentialState } from "@/features/shared/assistant/assistant-credential-support";
import {
  INCUBATOR_INPUT_MAX_LENGTH,
  INCUBATOR_PROMPT_SUGGESTIONS,
} from "@/features/lobby/components/incubator/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator/incubator-page-model";

export type VisibleChatMessage = IncubatorChatModel["messages"][number] & {
  role: "assistant" | "user";
};

export function CredentialNoticeCard({
  credentialSettingsHref,
  message,
}: {
  credentialSettingsHref: string;
  message: string;
}) {
  return (
    <div className="callout-warning flex flex-wrap items-center gap-2 px-2.5 py-2 text-[10.5px] leading-5 text-accent-warning">
      <p className="min-w-0 flex-1 break-words">{message}</p>
      <Link
        className="inline-flex shrink-0 items-center rounded-full bg-glass px-2 py-0.5 text-[10px] font-medium text-accent-primary transition hover:bg-elevated"
        href={credentialSettingsHref}
      >
        前往模型连接
      </Link>
    </div>
  );
}

export function PromptSuggestionBar({
  disabled,
  onSelect,
}: {
  disabled?: boolean;
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {INCUBATOR_PROMPT_SUGGESTIONS.map((prompt) => (
        <button
          className="ink-button-secondary !h-auto !text-left !text-[11px] !leading-5"
          disabled={disabled}
          key={prompt}
          type="button"
          onClick={() => onSelect(prompt)}
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}

export function MessageBubble({
  content,
  hookResults,
  role,
  status,
}: {
  content: string;
  hookResults?: IncubatorChatModel["messages"][number]["hookResults"];
  role: "assistant" | "user";
  status?: "pending" | "error";
}) {
  const isAssistant = role === "assistant";
  const alignmentClassName = isAssistant ? "self-start" : "self-end";
  const className = isAssistant
    ? "bg-glass-heavy text-text-primary shadow-sm"
    : "bg-accent-primary-muted text-text-primary shadow-sm";
  const statusClassName = resolveMessageStatusClassName(status);
  const documentMatch = isAssistant ? matchAssistantMarkdownDocument(content) : null;

  return (
    <article className={`max-w-[84%] md:max-w-[80%] xl:max-w-[78%] rounded-2xl border px-3 py-2 ${alignmentClassName} ${className} ${statusClassName}`}>
      <p className="text-[10px] font-medium tracking-[0.12em] text-text-secondary">
        {isAssistant ? "AI" : "你"}
      </p>
      {documentMatch ? (
        <div className="mt-1 space-y-2">
          {documentMatch.leadingText ? (
            <p className="whitespace-pre-wrap break-words text-[13px] leading-6">{documentMatch.leadingText}</p>
          ) : null}
          <section className="overflow-hidden rounded-2xl bg-muted shadow-sm">
            <header className="flex items-center justify-between gap-3 border-b border-line-soft bg-glass px-3 py-2">
              <div className="min-w-0">
                <p className="m-0 text-[10px] font-semibold tracking-[0.12em] uppercase text-text-secondary">Markdown 文档</p>
                <p className="m-0 text-[10px] leading-5 text-text-tertiary">已自动识别为整段文档。</p>
              </div>
              <button
                className="shrink-0 rounded-full bg-surface shadow-xs px-2.5 py-1 text-[10.5px] font-medium text-text-secondary transition hover:bg-glass-heavy hover:shadow-sm"
                type="button"
                onClick={() => {
                  void copyMarkdownDocument(documentMatch.body);
                }}
              >
                复制
              </button>
            </header>
            <pre className="m-0 max-w-full overflow-x-auto whitespace-pre-wrap break-words px-3 py-2.5 text-[12px] leading-6 text-text-primary [overflow-wrap:anywhere]">
              <code>{documentMatch.body}</code>
            </pre>
          </section>
          {documentMatch.trailingText ? (
            <p className="whitespace-pre-wrap break-words text-[13px] leading-6">{documentMatch.trailingText}</p>
          ) : null}
        </div>
      ) : (
        <p className="mt-1 whitespace-pre-wrap break-words text-[13px] leading-6">{content}</p>
      )}
      {isAssistant && hookResults && hookResults.length > 0 ? (
        <p className="mt-2 rounded-lg bg-muted px-2.5 py-1.5 text-[11px] leading-5 text-text-secondary">
          已执行 {hookResults.length} 个自动动作
        </p>
      ) : null}
    </article>
  );
}

export function buildCanSubmit(model: IncubatorChatModel) {
  return model.canChat && model.composerText.trim().length > 0 && !model.isCredentialLoading && !model.isResponding;
}

export function buildComposerHint(
  currentLength: number,
  credentialState: IncubatorCredentialState,
  canChat: boolean,
  isCredentialLoading: boolean,
) {
  if (isCredentialLoading || credentialState === "loading") {
    return "正在准备聊天。";
  }
  if (credentialState === "error") {
    return "模型连接读取失败，请检查后重试。";
  }
  if (credentialState === "empty") {
    return "请先启用模型连接。";
  }
  if (!canChat) {
    return "请选择模型连接。";
  }
  return `${currentLength} / ${INCUBATOR_INPUT_MAX_LENGTH} · 按回车发送，Shift + 回车换行`;
}

export function resolveSubmitButtonLabel(isCredentialLoading: boolean, isResponding: boolean) {
  if (isCredentialLoading) {
    return "正在准备聊天…";
  }
  if (isResponding) {
    return "AI 回复中…";
  }
  return "发送";
}

export function isVisibleConversationMessage(
  message: IncubatorChatModel["messages"][number],
): message is VisibleChatMessage {
  return !message.hidden && (message.role === "assistant" || message.role === "user");
}

function resolveMessageStatusClassName(status: "pending" | "error" | undefined) {
  if (status === "error") {
    return "border-accent-danger/15 bg-accent-danger/10";
  }
  if (status === "pending") {
    return "border-accent-info-muted bg-accent-info-soft";
  }
  return "border-transparent shadow-xs";
}

async function copyMarkdownDocument(content: string) {
  try {
    await navigator.clipboard.writeText(content);
    showAppNotice({ content: "已复制到剪贴板。", tone: "success" });
  } catch {
    showAppNotice({
      content: "复制失败，请检查浏览器剪贴板权限后重试。",
      tone: "danger",
    });
  }
}
