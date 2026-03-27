"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { getErrorMessage } from "@/lib/api/client";
import { runAssistantTurn } from "@/lib/api/assistant";
import { buildIncubatorConversationDraft, createProject } from "@/lib/api/projects";
import type { AssistantTurnResult, ProjectIncubatorConversationDraft, ProjectSetting } from "@/lib/api/types";

import {
  buildAssistantModelOverride,
  buildAssistantTurnMessages,
  buildIncubatorConversationFingerprint,
  buildIncubatorConversationText,
  buildSuggestedProjectName,
  createIncubatorInitialMessages,
  createIncubatorMessage,
  INCUBATOR_CHAT_SKILL_ID,
  INITIAL_INCUBATOR_CHAT_SETTINGS,
  replaceIncubatorMessage,
  resolveIncubatorModelName,
  resolveIncubatorProvider,
  type IncubatorChatMessage,
  type IncubatorChatSettings,
} from "./incubator-chat-support";
import { buildErrorFeedback, type FeedbackState } from "./incubator-feedback-support";

type DraftSyncParams = {
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  messages: IncubatorChatMessage[];
  setDraftFingerprint: Dispatch<SetStateAction<string | null>>;
  setFeedback?: Dispatch<SetStateAction<FeedbackState | null>>;
  settings: IncubatorChatSettings;
};

type SubmitPromptParams = DraftSyncParams & {
  assistantMutation: UseMutationResult<AssistantTurnResult, unknown, IncubatorChatMessage[]>;
  isResponding: boolean;
  setComposerText: Dispatch<SetStateAction<string>>;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
  setMessages: Dispatch<SetStateAction<IncubatorChatMessage[]>>;
};

export function useChatState() {
  const [composerText, setComposerText] = useState("");
  const [messages, setMessages] = useState<IncubatorChatMessage[]>(createIncubatorInitialMessages);
  const [settings, setSettings] = useState(INITIAL_INCUBATOR_CHAT_SETTINGS);
  const [projectName, setProjectNameState] = useState("");
  const [hasCustomProjectName, setHasCustomProjectName] = useState(false);
  const [draftFingerprint, setDraftFingerprint] = useState<string | null>(null);
  return {
    composerText,
    draftFingerprint,
    hasCustomProjectName,
    messages,
    projectName,
    setComposerText,
    setDraftFingerprint,
    setHasCustomProjectName,
    setMessages,
    setProjectNameState,
    settings,
    setSettings,
  };
}

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
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>,
) {
  return useMutation({
    mutationFn: (conversationText: string) =>
      buildIncubatorConversationDraft({
        conversation_text: conversationText,
        provider: resolveIncubatorProvider(settings.provider),
        model_name: resolveIncubatorModelName(settings.modelName) || undefined,
      }),
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });
}

export function useIncubatorCreateMutation({
  draftSetting,
  projectName,
  setFeedback,
  settings,
}: {
  draftSetting: ProjectSetting | null;
  projectName: string;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
  settings: IncubatorChatSettings;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: () =>
      createProject({
        name: projectName.trim(),
        project_setting: draftSetting,
        allow_system_credential_pool: settings.allowSystemCredentialPool,
      }),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/workspace/project/${result.id}/studio?panel=setting`);
    },
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });
}

export function useIncubatorAssistantMutation(settings: IncubatorChatSettings) {
  return useMutation({
    mutationFn: (messages: IncubatorChatMessage[]) =>
      runAssistantTurn({
        skill_id: INCUBATOR_CHAT_SKILL_ID,
        messages: buildAssistantTurnMessages(messages),
        model: buildAssistantModelOverride(settings),
      }),
  });
}

export function useSuggestedProjectName(
  draftSetting: ProjectSetting | null,
  hasCustomProjectName: boolean,
  setProjectNameState: Dispatch<SetStateAction<string>>,
) {
  useEffect(() => {
    if (!draftSetting || hasCustomProjectName) return;
    setProjectNameState(buildSuggestedProjectName(draftSetting));
  }, [draftSetting, hasCustomProjectName, setProjectNameState]);
}

export function useIncubatorDraftSync({
  draftMutation,
  messages,
  setDraftFingerprint,
  setFeedback,
  settings,
}: DraftSyncParams) {
  return useCallback(async () => {
    setFeedback?.(null);
    try {
      await syncConversationDraft({ draftMutation, messages, setDraftFingerprint, settings });
    } catch {
      return;
    }
  }, [draftMutation, messages, setDraftFingerprint, setFeedback, settings]);
}

export function useIncubatorPromptSubmit({
  assistantMutation,
  draftMutation,
  isResponding,
  messages,
  setComposerText,
  setDraftFingerprint,
  setFeedback,
  setMessages,
  settings,
}: SubmitPromptParams) {
  return useCallback(async (prompt: string) => {
    const submission = buildPromptSubmission(prompt, messages, isResponding);
    if (!submission) return;
    setFeedback(null);
    setComposerText("");
    setMessages(submission.nextMessages);
    try {
      await completePromptSubmission({
        assistantMutation,
        draftMutation,
        setDraftFingerprint,
        setMessages,
        settings,
        submission,
      });
    } catch (error) {
      handlePromptSubmissionError(error, setFeedback, setMessages, submission);
    }
  }, [
    assistantMutation,
    draftMutation,
    isResponding,
    messages,
    setComposerText,
    setDraftFingerprint,
    setFeedback,
    setMessages,
    settings,
  ]);
}

function buildPromptSubmission(prompt: string, messages: IncubatorChatMessage[], isResponding: boolean) {
  const content = prompt.trim();
  if (!content || isResponding) return null;
  const userMessage = createIncubatorMessage("user", content);
  const pendingAssistant = createIncubatorMessage("assistant", "正在整理故事方向…", { status: "pending" });
  const submittedMessages = [...messages, userMessage];
  return { nextMessages: [...submittedMessages, pendingAssistant], pendingAssistant, submittedMessages };
}

async function completePromptSubmission({
  assistantMutation,
  draftMutation,
  setDraftFingerprint,
  setMessages,
  settings,
  submission,
}: {
  assistantMutation: UseMutationResult<AssistantTurnResult, unknown, IncubatorChatMessage[]>;
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  setDraftFingerprint: Dispatch<SetStateAction<string | null>>;
  setMessages: Dispatch<SetStateAction<IncubatorChatMessage[]>>;
  settings: IncubatorChatSettings;
  submission: NonNullable<ReturnType<typeof buildPromptSubmission>>;
}) {
  const result = await assistantMutation.mutateAsync(submission.submittedMessages);
  const resolvedMessages = replaceIncubatorMessage(
    submission.nextMessages,
    submission.pendingAssistant.id,
    createIncubatorMessage("assistant", result.content),
  );
  setMessages(resolvedMessages);
  await syncConversationDraft({ draftMutation, messages: resolvedMessages, setDraftFingerprint, settings });
}

function handlePromptSubmissionError(
  error: unknown,
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>,
  setMessages: Dispatch<SetStateAction<IncubatorChatMessage[]>>,
  submission: NonNullable<ReturnType<typeof buildPromptSubmission>>,
) {
  setMessages(replaceIncubatorMessage(
    submission.nextMessages,
    submission.pendingAssistant.id,
    createIncubatorMessage("assistant", getErrorMessage(error), { status: "error" }),
  ));
  setFeedback(buildErrorFeedback(error));
}

async function syncConversationDraft({
  draftMutation,
  messages,
  setDraftFingerprint,
  settings,
}: DraftSyncParams) {
  const conversationText = buildIncubatorConversationText(messages);
  if (!conversationText) return;
  await draftMutation.mutateAsync(conversationText);
  setDraftFingerprint(buildIncubatorConversationFingerprint(messages, settings));
}

export function isDraftStale(
  draft: ProjectIncubatorConversationDraft | undefined,
  draftFingerprint: string | null,
  conversationFingerprint: string,
) {
  return Boolean(draft) && draftFingerprint !== null && draftFingerprint !== conversationFingerprint;
}
