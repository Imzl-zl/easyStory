"use client";

import Link from "next/link";

import type { IncubatorCredentialState } from "@/features/lobby/components/incubator-chat-credential-support";
import {
  INCUBATOR_INPUT_MAX_LENGTH,
  INCUBATOR_PROMPT_SUGGESTIONS,
} from "@/features/lobby/components/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator-page-model";

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
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-[rgba(183,121,31,0.14)] bg-[rgba(183,121,31,0.1)] px-3 py-2 text-[11.5px] leading-5 text-[var(--accent-warning)]">
      <p className="min-w-0 flex-1">{message}</p>
      <Link
        className="inline-flex shrink-0 items-center rounded-full bg-[rgba(255,255,255,0.76)] px-2 py-0.5 text-[10.5px] font-medium text-[var(--accent-ink)] transition hover:bg-[rgba(255,255,255,0.96)]"
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
          className="rounded-full border border-[var(--line-soft)] bg-[rgba(255,255,255,0.92)] px-2.5 py-1 text-left text-[11px] leading-5 text-[var(--text-primary)] transition-[border-color,background-color,color] hover:border-[rgba(46,111,106,0.18)] hover:bg-[rgba(46,111,106,0.08)] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          key={prompt}
          onClick={() => onSelect(prompt)}
          type="button"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}

export function MessageBubble({
  content,
  role,
  status,
}: {
  content: string;
  role: "assistant" | "user";
  status?: "pending" | "error";
}) {
  const isAssistant = role === "assistant";
  const alignmentClassName = isAssistant ? "self-start" : "self-end";
  const className = isAssistant
    ? "bg-[rgba(255,251,245,0.96)] text-[var(--text-primary)] shadow-[0_10px_22px_rgba(58,45,29,0.05)]"
    : "bg-[rgba(46,111,106,0.14)] text-[var(--text-primary)] shadow-[0_10px_18px_rgba(46,111,106,0.08)]";
  const statusClassName = resolveMessageStatusClassName(status);

  return (
    <article className={`max-w-[84%] md:max-w-[80%] xl:max-w-[78%] rounded-[16px] border px-3 py-2 ${alignmentClassName} ${className} ${statusClassName}`}>
      <p className="text-[10px] font-medium tracking-[0.12em] text-[var(--text-secondary)]">
        {isAssistant ? "AI" : "你"}
      </p>
      <p className="mt-1 whitespace-pre-wrap break-words text-[13px] leading-6">{content}</p>
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
    return "border-[rgba(178,65,46,0.16)] bg-[rgba(178,65,46,0.1)]";
  }
  if (status === "pending") {
    return "border-[rgba(58,124,165,0.14)] bg-[rgba(58,124,165,0.08)]";
  }
  return "border-[var(--line-soft)]";
}
