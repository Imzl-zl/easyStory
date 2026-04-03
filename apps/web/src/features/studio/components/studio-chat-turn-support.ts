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
  },
): StudioChatSession {
  const normalized = normalizeStudioAssistantReply(options.content);
  return {
    ...current,
    ...(options.consumedNextTurnSkillId ? { nextTurnSkillId: null } : {}),
    messages: replaceStudioChatMessage(current.messages, options.messageId, {
      content: normalized.content,
      id: options.messageId,
      rawMarkdown: options.content,
      role: "assistant",
      status: normalized.status,
    }),
  };
}
