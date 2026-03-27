"use client";

import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult } from "@tanstack/react-query";

import type { ProjectDetail, ProjectIncubatorConversationDraft } from "@/lib/api/types";

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
  composerText: string;
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  hasUserMessage: boolean;
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
  const conversationFingerprint = useConversationFingerprint(state.messages, state.settings);
  const draftMutation = useIncubatorDraftMutation(state.settings, setFeedback);
  const createMutation = useIncubatorCreateMutation({
    draftSetting: draftMutation.data?.project_setting ?? null,
    projectName: state.projectName,
    setFeedback,
    settings: state.settings,
  });
  const assistantMutation = useIncubatorAssistantMutation(state.settings);
  const submitPrompt = useIncubatorPromptSubmit({
    assistantMutation,
    draftMutation,
    isResponding: assistantMutation.isPending,
    messages: state.messages,
    setComposerText: state.setComposerText,
    setDraftFingerprint: state.setDraftFingerprint,
    setFeedback,
    setMessages: state.setMessages,
    settings: state.settings,
  });
  const syncDraft = useIncubatorDraftSync({
    draftMutation,
    messages: state.messages,
    setDraftFingerprint: state.setDraftFingerprint,
    setFeedback,
    settings: state.settings,
  });

  useSuggestedProjectName(
    draftMutation.data?.project_setting ?? null,
    state.hasCustomProjectName,
    state.setProjectNameState,
  );

  return {
    composerText: state.composerText,
    createMutation,
    draftMutation,
    hasUserMessage: state.messages.some((message) => message.role === "user"),
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
    submitPrompt,
    syncDraft,
  };
}
