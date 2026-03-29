"use client";

import { ApiError, getErrorMessage } from "@/lib/api/client";
import type { AssistantTurnPayload } from "@/lib/api/types";

import {
  buildAssistantModelOverride,
  buildAssistantTurnMessages,
  INCUBATOR_CHAT_SKILL_ID,
  type IncubatorChatMessage,
  type IncubatorChatSettings,
} from "./incubator-chat-support";

const NON_RETRYABLE_STREAM_STATUSES = new Set([400, 401, 403, 404, 422]);

export function buildIncubatorAssistantTurnPayload(
  settings: IncubatorChatSettings,
  messages: IncubatorChatMessage[],
): AssistantTurnPayload {
  return {
    messages: buildAssistantTurnMessages(messages),
    model: buildAssistantModelOverride(settings),
    skill_id: INCUBATOR_CHAT_SKILL_ID,
  };
}

export function shouldRetryAssistantWithoutStream(error: unknown) {
  if (error instanceof ApiError) {
    return !NON_RETRYABLE_STREAM_STATUSES.has(error.status);
  }
  return true;
}

export function buildAssistantStreamRecoveryNotice() {
  return "实时回复不稳定，系统已自动改为完整返回。你也可以在“模型与连接”里切换成“生成后整体显示”。";
}

export function buildAssistantRetryFailure(error: unknown, retryError: unknown) {
  const firstMessage = getErrorMessage(error);
  const retryMessage = getErrorMessage(retryError);
  return new Error(
    `实时回复失败，且自动重试完整返回也没有成功。第一次错误：${firstMessage}；重试错误：${retryMessage}`,
  );
}
