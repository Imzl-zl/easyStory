import {
  finalizeStudioChatToolProgress,
  normalizeStudioAssistantReply,
  replaceStudioChatMessage,
  resolveStudioFailedReply,
  type StudioChatToolProgressTerminalReason,
} from "@/features/studio/components/chat/studio-chat-support";
import type { StudioChatSession } from "@/features/studio/components/chat/studio-chat-store-support";

export function buildSucceededStudioConversationSession(
  current: StudioChatSession,
  options: {
    consumedNextTurnSkillId: string | null;
    content: string;
    messageId: string;
    runId: string;
  },
): StudioChatSession {
  const normalized = normalizeStudioAssistantReply(options.content);
  const currentMessage = current.messages.find((message) => message.id === options.messageId);
  return {
    ...current,
    ...(options.consumedNextTurnSkillId ? { nextTurnSkillId: null } : {}),
    latestCompletedRunId: normalized.status === "error" ? null : options.runId,
    messages: replaceStudioChatMessage(current.messages, options.messageId, {
      content: normalized.content,
      id: options.messageId,
      rawMarkdown: normalized.content,
      requestContent: normalized.content,
      role: "assistant",
      status: normalized.status,
      toolProgress: currentMessage?.toolProgress,
    }),
  };
}

export function buildFailedStudioConversationSession(
  current: StudioChatSession,
  options: {
    errorMessage: string;
    messageId: string;
    terminalReason: StudioChatToolProgressTerminalReason;
  },
): StudioChatSession {
  const currentMessage = current.messages.find((message) => message.id === options.messageId);
  const failedContent = resolveStudioFailedReply(
    currentMessage?.content ?? "",
    options.errorMessage,
  );
  const resolvedContent = failedContent ?? options.errorMessage;
  return {
    ...current,
    latestCompletedRunId: null,
    messages: replaceStudioChatMessage(current.messages, options.messageId, {
      content: resolvedContent,
      id: options.messageId,
      rawMarkdown: resolvedContent,
      requestContent: resolvedContent,
      role: "assistant",
      status: "error",
      toolProgress: finalizeStudioChatToolProgress(
        currentMessage?.toolProgress,
        options.terminalReason,
      ),
    }),
  };
}
