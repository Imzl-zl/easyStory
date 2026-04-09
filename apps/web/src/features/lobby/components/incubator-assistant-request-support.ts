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

export function buildIncubatorAssistantTurnPayload(options: {
  apiDialect?: string | null;
  conversationId: string;
  defaultModelName?: string | null;
  latestCompletedRunId: string | null;
  settings: IncubatorChatSettings;
  messages: IncubatorChatMessage[];
}): AssistantTurnPayload {
  const agentId = resolveIncubatorAgentId(options.settings.agentId);
  const skillId = resolveIncubatorSkillId(options.settings.skillId);
  const currentUserMessage = options.messages[options.messages.length - 1];
  if (!currentUserMessage || currentUserMessage.role !== "user") {
    throw new Error("Incubator assistant turn payload requires a latest user message.");
  }
  return {
    conversation_id: options.conversationId,
    client_turn_id: currentUserMessage.id,
    hook_ids: resolveIncubatorHookIds(options.settings.hookIds),
    messages: buildAssistantTurnMessages(options.messages),
    model: buildAssistantModelOverride(options.settings, {
      apiDialect: options.apiDialect,
      defaultModelName: options.defaultModelName,
    }),
    ...(options.latestCompletedRunId
      ? {
        continuation_anchor: {
          previous_run_id: options.latestCompletedRunId,
        },
      }
      : {}),
    requested_write_scope: "disabled",
    ...(agentId
      ? { agent_id: agentId }
      : skillId ? { skill_id: skillId } : {}),
  };
}
