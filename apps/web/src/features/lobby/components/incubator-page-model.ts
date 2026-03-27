"use client";

import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult } from "@tanstack/react-query";

import type { ProjectDetail, ProjectIncubatorConversationDraft } from "@/lib/api/types";

import type { IncubatorCredentialOption } from "./incubator-chat-credential-support";
import { useIncubatorChatCredentialModel } from "./incubator-chat-credential-model";
import type {
  IncubatorChatMessage,
  IncubatorChatSettings,
} from "./incubator-chat-support";
import type { FeedbackState } from "./incubator-feedback-support";
import {
  isDraftStale,
  useChatState,
  useConversationFingerprint,
  useIncubatorAssistantMutation,
  useIncubatorCreateMutation,
  useIncubatorDraftMutation,
  useIncubatorDraftSync,
  useIncubatorPromptSubmit,
  useProjectNameSetter,
  useSuggestedProjectName,
} from "./incubator-page-model-support";

export type IncubatorChatModel = {
  applyPromptSuggestion: (prompt: string) => void;
  canChat: boolean;
  composerText: string;
  credentialNotice: string | null;
  credentialOptions: IncubatorCredentialOption[];
  credentialSettingsHref: string;
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  hasUserMessage: boolean;
  isCredentialLoading: boolean;
  isDraftStale: boolean;
  isResponding: boolean;
  messages: IncubatorChatMessage[];
  projectName: string;
  setComposerText: Dispatch<SetStateAction<string>>;
  settings: IncubatorChatSettings;
  setProjectName: (value: string) => void;
  setSettings: Dispatch<SetStateAction<IncubatorChatSettings>>;
  submitPrompt: (prompt: string) => Promise<void>;
  syncDraft: () => Promise<void>;
};

export function useIncubatorChatModel(
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>,
): IncubatorChatModel {
  const state = useChatState();
  const credentialModel = useIncubatorChatCredentialModel(state.settings, state.setSettings);
  const conversationFingerprint = useConversationFingerprint(state.messages, state.settings);
  const draftMutation = useIncubatorDraftMutation(state.settings);
  const createMutation = useIncubatorCreateMutation({
    draftSetting: draftMutation.data?.project_setting ?? null,
    projectName: state.projectName,
    setFeedback,
    settings: state.settings,
  });
  const assistantMutation = useIncubatorAssistantMutation(state.settings);
  const baseSubmitPrompt = useIncubatorPromptSubmit({
    assistantMutation,
    isResponding: assistantMutation.isPending,
    messages: state.messages,
    setComposerText: state.setComposerText,
    setFeedback,
    setMessages: state.setMessages,
  });
  const syncDraft = useIncubatorDraftSync({
    draftMutation,
    messages: state.messages,
    setDraftFingerprint: state.setDraftFingerprint,
    settings: state.settings,
  });

  useSuggestedProjectName(
    draftMutation.data?.project_setting ?? null,
    state.hasCustomProjectName,
    state.setProjectNameState,
  );

  return {
    applyPromptSuggestion: (prompt: string) => state.setComposerText(prompt),
    canChat: credentialModel.canChat,
    composerText: state.composerText,
    credentialNotice: credentialModel.credentialNotice,
    credentialOptions: credentialModel.credentialOptions,
    credentialSettingsHref: credentialModel.credentialSettingsHref,
    createMutation,
    draftMutation,
    hasUserMessage: state.messages.some((message) => message.role === "user"),
    isCredentialLoading: credentialModel.isCredentialLoading,
    isDraftStale: isDraftStale(
      draftMutation.data,
      state.draftFingerprint,
      conversationFingerprint,
    ),
    isResponding: assistantMutation.isPending,
    messages: state.messages,
    projectName: state.projectName,
    setComposerText: state.setComposerText,
    settings: state.settings,
    setProjectName: useProjectNameSetter(
      state.setHasCustomProjectName,
      state.setProjectNameState,
    ),
    setSettings: state.setSettings,
    submitPrompt: async (prompt: string) => {
      if (!credentialModel.canChat || credentialModel.isCredentialLoading) {
        return;
      }
      await baseSubmitPrompt(prompt);
    },
    syncDraft,
  };
}
