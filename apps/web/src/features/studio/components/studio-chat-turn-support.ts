import {
  normalizeStudioAssistantReply,
  replaceStudioChatMessage,
} from "./studio-chat-support";
import type { StudioChatSession } from "./studio-chat-store-support";

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
    latestCompletedRunId: options.runId,
    messages: replaceStudioChatMessage(current.messages, options.messageId, {
      content: normalized.content,
      id: options.messageId,
      rawMarkdown: options.content,
      requestContent: options.content,
      role: "assistant",
      status: normalized.status,
      toolProgress: currentMessage?.toolProgress,
    }),
  };
}
