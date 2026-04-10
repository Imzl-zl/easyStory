"use client";

import { useCallback, useEffect, useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { runAssistantTurn, runAssistantTurnStream } from "@/lib/api/assistant";
import { buildIncubatorConversationDraft, createProject } from "@/lib/api/projects";
import type { AssistantTurnResult, ProjectIncubatorConversationDraft, ProjectSetting } from "@/lib/api/types";

import {
  buildIncubatorAssistantTurnPayload,
} from "@/features/lobby/components/incubator/incubator-assistant-request-support";
import { useChatState } from "@/features/lobby/components/incubator/incubator-chat-state";
import {
  appendIncubatorMessageDelta,
  buildIncubatorConversationFingerprint,
  buildSuggestedProjectName,
  resolveIncubatorModelName,
  resolveIncubatorProvider,
  type IncubatorChatMessage,
  type IncubatorChatSettings,
} from "@/features/lobby/components/incubator/incubator-chat-support";
import {
  buildPromptSubmission,
  completePromptSubmission,
  handlePromptSubmissionError,
  isDraftStale,
  syncConversationDraft,
  type PromptSubmission,
} from "@/features/lobby/components/incubator/incubator-chat-submit-support";
import type { IncubatorChatSession } from "@/features/lobby/components/incubator/incubator-chat-store";
import { buildErrorFeedback, type FeedbackState } from "@/features/lobby/components/incubator/incubator-feedback-support";

type DraftSyncSubmission = {
  conversationFingerprint: string;
  conversationId: string;
  conversationText: string;
};

export type IncubatorConversationDraftMutation = UseMutationResult<
  ProjectIncubatorConversationDraft,
  unknown,
  DraftSyncSubmission
>;

type DraftSyncParams = {
  activeConversationId: string;
  draftMutation: IncubatorConversationDraftMutation;
  messages: IncubatorChatMessage[];
  settings: IncubatorChatSettings;
};

type SubmitPromptParams = {
  activeConversationId: string;
  assistantMutation: UseMutationResult<AssistantTurnResult, unknown, PromptSubmission>;
  isResponding: boolean;
  messages: IncubatorChatMessage[];
  patchConversationSession: (
    conversationId: string,
    updater: (current: IncubatorChatSession) => IncubatorChatSession,
  ) => void;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
};

export { useChatState };
export { isDraftStale } from "@/features/lobby/components/incubator/incubator-chat-submit-support";

export function useProjectNameSetter(
  setHasCustomProjectName: Dispatch<SetStateAction<boolean>>,
  setProjectNameState: Dispatch<SetStateAction<string>>,
) {
  return useCallback((value: string) => {
    setHasCustomProjectName(true);
    setProjectNameState(value);
  }, [setHasCustomProjectName, setProjectNameState]);
}

export function useConversationFingerprint(
  messages: IncubatorChatMessage[],
  settings: IncubatorChatSettings,
) {
  return useMemo(() => buildIncubatorConversationFingerprint(messages, settings), [messages, settings]);
}

export function useIncubatorDraftMutation(
  settings: IncubatorChatSettings,
  patchConversationSession: SubmitPromptParams["patchConversationSession"],
): IncubatorConversationDraftMutation {
  return useMutation({
    mutationFn: ({ conversationText }: DraftSyncSubmission) =>
      buildIncubatorConversationDraft({
        conversation_text: conversationText,
        model_name: resolveIncubatorModelName(settings.modelName) || undefined,
        provider: resolveIncubatorProvider(settings.provider),
      }),
    onSuccess: (draft, variables) => {
      patchConversationSession(variables.conversationId, (current) => ({
        ...current,
        draft,
        draftFingerprint: variables.conversationFingerprint,
      }));
    },
  });
}

export function useIncubatorCreateMutation({
  draftSetting,
  onCreated,
  projectName,
  setFeedback,
  settings,
}: {
  draftSetting: ProjectSetting | null;
  onCreated: () => void;
  projectName: string;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
  settings: IncubatorChatSettings;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: () =>
      createProject({
        allow_system_credential_pool: settings.allowSystemCredentialPool,
        name: projectName.trim(),
        project_setting: draftSetting,
      }),
    onSuccess: async (result) => {
      onCreated();
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/workspace/project/${result.id}/studio?panel=setting&doc=${encodeURIComponent("项目说明.md")}`);
    },
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });
}

export function useIncubatorAssistantMutation(
  settings: IncubatorChatSettings,
  latestCompletedRunId: string | null,
  patchConversationSession: SubmitPromptParams["patchConversationSession"],
  selectedCredentialApiDialect: string | null,
  selectedCredentialDefaultModel: string | null,
) {
  return useMutation({
    mutationFn: async (submission: PromptSubmission) => {
      const payload = buildIncubatorAssistantTurnPayload({
        apiDialect: selectedCredentialApiDialect,
        conversationId: submission.conversationId,
        defaultModelName: selectedCredentialDefaultModel,
        latestCompletedRunId,
        messages: submission.submittedMessages,
        settings,
      });
      if (!settings.streamOutput) {
        return runAssistantTurn(payload);
      }
      return runAssistantTurnStream(payload, {
        onChunk: (delta) => {
          patchConversationSession(submission.conversationId, (current) => ({
            ...current,
            messages: appendIncubatorMessageDelta(current.messages, submission.pendingAssistant.id, delta),
          }));
        },
      });
    },
  });
}

export function useSuggestedProjectName(
  draftSetting: ProjectSetting | null,
  hasCustomProjectName: boolean,
  setProjectNameState: Dispatch<SetStateAction<string>>,
) {
  useEffect(() => {
    if (!draftSetting || hasCustomProjectName) {
      return;
    }
    setProjectNameState(buildSuggestedProjectName(draftSetting));
  }, [draftSetting, hasCustomProjectName, setProjectNameState]);
}

export function useIncubatorDraftSync({
  activeConversationId,
  draftMutation,
  messages,
  settings,
}: DraftSyncParams) {
  return useCallback(async () => {
    try {
      draftMutation.reset();
      await syncConversationDraft(activeConversationId, draftMutation, messages, settings);
    } catch {
      return;
    }
  }, [activeConversationId, draftMutation, messages, settings]);
}

export function useIncubatorPromptSubmit({
  activeConversationId,
  assistantMutation,
  isResponding,
  messages,
  patchConversationSession,
  setFeedback,
}: SubmitPromptParams) {
  return useCallback(async (prompt: string) => {
    const submission = buildPromptSubmission(prompt, messages, isResponding, activeConversationId);
    if (!submission) {
      return;
    }
    setFeedback(null);
    patchConversationSession(submission.conversationId, (current) => ({
      ...current,
      composerText: "",
      messages: submission.nextMessages,
    }));
    try {
      await completePromptSubmission(assistantMutation, patchConversationSession, submission);
    } catch (error) {
      handlePromptSubmissionError(error, patchConversationSession, setFeedback, submission);
    }
  }, [
    activeConversationId,
    assistantMutation,
    isResponding,
    messages,
    patchConversationSession,
    setFeedback,
  ]);
}
