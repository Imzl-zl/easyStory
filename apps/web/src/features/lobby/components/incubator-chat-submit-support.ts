"use client";

import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult } from "@tanstack/react-query";

import { getErrorMessage } from "@/lib/api/client";
import type { AssistantTurnResult, ProjectIncubatorConversationDraft } from "@/lib/api/types";

import {
  buildIncubatorConversationFingerprint,
  buildIncubatorConversationText,
  createIncubatorMessage,
  INCUBATOR_PENDING_REPLY_MESSAGE,
  replaceIncubatorMessage,
  resolveIncubatorAssistantReply,
  resolveFailedIncubatorReply,
  type IncubatorChatMessage,
  type IncubatorChatSettings,
} from "./incubator-chat-support";
import type { IncubatorChatSession } from "./incubator-chat-store";
import { buildErrorFeedback, type FeedbackState } from "./incubator-feedback-support";

export type PromptSubmission = {
  conversationId: string;
  nextMessages: IncubatorChatMessage[];
  pendingAssistant: IncubatorChatMessage;
  submittedMessages: IncubatorChatMessage[];
};

type ConversationSessionPatcher = (
  conversationId: string,
  updater: (current: IncubatorChatSession) => IncubatorChatSession,
) => void;

export function isDraftStale(
  draft: ProjectIncubatorConversationDraft | null,
  draftFingerprint: string | null,
  conversationFingerprint: string,
) {
  return Boolean(draft) && draftFingerprint !== null && draftFingerprint !== conversationFingerprint;
}

export function buildPromptSubmission(
  prompt: string,
  messages: IncubatorChatMessage[],
  isResponding: boolean,
  conversationId: string,
) {
  const content = prompt.trim();
  if (!content || isResponding) {
    return null;
  }
  const userMessage = createIncubatorMessage("user", content);
  const pendingAssistant = createIncubatorMessage("assistant", INCUBATOR_PENDING_REPLY_MESSAGE, { status: "pending" });
  const submittedMessages = [...messages, userMessage];
  return {
    conversationId,
    nextMessages: [...submittedMessages, pendingAssistant],
    pendingAssistant,
    submittedMessages,
  };
}

export async function completePromptSubmission(
  assistantMutation: UseMutationResult<AssistantTurnResult, unknown, PromptSubmission>,
  patchConversationSession: ConversationSessionPatcher,
  submission: PromptSubmission,
) {
  const result = await assistantMutation.mutateAsync(submission);
  const assistantReply = resolveIncubatorAssistantReply(result.content);
  patchConversationSession(submission.conversationId, (current) => ({
    ...current,
    latestCompletedRunId: assistantReply.status === "error" ? null : result.run_id,
    messages: replaceIncubatorMessage(
      submission.nextMessages,
      submission.pendingAssistant.id,
      createIncubatorMessage("assistant", assistantReply.content, {
        hookResults: result.hook_results,
        status: assistantReply.status,
      }),
    ),
  }));
}

export function handlePromptSubmissionError(
  error: unknown,
  patchConversationSession: ConversationSessionPatcher,
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>,
  submission: PromptSubmission,
) {
  const errorMessage = getErrorMessage(error);
  setFeedback(buildErrorFeedback(error));
  patchConversationSession(submission.conversationId, (current) => {
    const currentPending = current.messages.find((message) => message.id === submission.pendingAssistant.id);
    const failedReply = currentPending ? resolveFailedIncubatorReply(currentPending.content, errorMessage) : null;
    return {
      ...current,
      latestCompletedRunId: null,
      messages: replaceIncubatorMessage(
        failedReply ? current.messages : submission.nextMessages,
        submission.pendingAssistant.id,
        createIncubatorMessage("assistant", failedReply ?? errorMessage, { status: "error" }),
      ),
    };
  });
}

export async function syncConversationDraft(
  activeConversationId: string,
  draftMutation: UseMutationResult<
    ProjectIncubatorConversationDraft,
    unknown,
    {
      conversationFingerprint: string;
      conversationId: string;
      conversationText: string;
    }
  >,
  messages: IncubatorChatMessage[],
  settings: IncubatorChatSettings,
) {
  const conversationText = buildIncubatorConversationText(messages);
  if (!conversationText) {
    return;
  }
  await draftMutation.mutateAsync({
    conversationFingerprint: buildIncubatorConversationFingerprint(messages, settings),
    conversationId: activeConversationId,
    conversationText,
  });
}
