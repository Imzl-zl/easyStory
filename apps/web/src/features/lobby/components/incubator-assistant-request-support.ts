"use client";

import type { AssistantTurnPayload } from "@/lib/api/types";

import {
  buildAssistantModelOverride,
  buildAssistantTurnMessages,
  resolveIncubatorAgentId,
  resolveIncubatorHookIds,
  resolveIncubatorSkillId,
  type IncubatorChatMessage,
  type IncubatorChatSettings,
} from "./incubator-chat-support";

export function buildIncubatorAssistantTurnPayload(
  conversationId: string,
  settings: IncubatorChatSettings,
  messages: IncubatorChatMessage[],
): AssistantTurnPayload {
  const agentId = resolveIncubatorAgentId(settings.agentId);
  const skillId = resolveIncubatorSkillId(settings.skillId);
  const currentUserMessage = [...messages].reverse().find((message) => message.role === "user");
  if (!currentUserMessage) {
    throw new Error("Incubator assistant turn payload requires a latest user message.");
  }
  return {
    conversation_id: conversationId,
    client_turn_id: currentUserMessage.id,
    hook_ids: resolveIncubatorHookIds(settings.hookIds),
    messages: buildAssistantTurnMessages(messages),
    model: buildAssistantModelOverride(settings),
    requested_write_scope: "disabled",
    ...(agentId
      ? { agent_id: agentId }
      : skillId ? { skill_id: skillId } : {}),
  };
}
