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
  settings: IncubatorChatSettings,
  messages: IncubatorChatMessage[],
): AssistantTurnPayload {
  const agentId = resolveIncubatorAgentId(settings.agentId);
  return {
    hook_ids: resolveIncubatorHookIds(settings.hookIds),
    messages: buildAssistantTurnMessages(messages),
    model: buildAssistantModelOverride(settings),
    ...(agentId
      ? { agent_id: agentId }
      : { skill_id: resolveIncubatorSkillId(settings.skillId) }),
  };
}
