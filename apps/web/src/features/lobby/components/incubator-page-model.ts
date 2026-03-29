"use client";

import { useEffect, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult } from "@tanstack/react-query";

import type { ProjectDetail, ProjectIncubatorConversationDraft } from "@/lib/api/types";

import type {
  IncubatorCredentialOption,
  IncubatorCredentialState,
} from "./incubator-chat-credential-support";
import { useIncubatorChatCredentialModel } from "./incubator-chat-credential-model";
import type {
  IncubatorChatMessage,
  IncubatorChatSettings,
} from "./incubator-chat-support";
import type { IncubatorConversationSummary } from "./incubator-chat-store";
import type { FeedbackState } from "./incubator-feedback-support";
import {
  type IncubatorConversationDraftMutation,
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
  activeConversationId: string;
  applyPromptSuggestion: (prompt: string) => void;
  canChat: boolean;
  composerText: string;
  conversationSummaries: IncubatorConversationSummary[];
  credentialNotice: string | null;
  credentialOptions: IncubatorCredentialOption[];
  credentialSettingsHref: string;
  credentialState: IncubatorCredentialState;
  createConversation: () => void;
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  deleteConversation: (conversationId: string) => void;
  draft: ProjectIncubatorConversationDraft | null;
  draftMutation: IncubatorConversationDraftMutation;
  hasUserMessage: boolean;
  isConversationBusy: boolean;
  isCredentialLoading: boolean;
  isDraftStale: boolean;
  isResponding: boolean;
  messages: IncubatorChatMessage[];
  projectName: string;
  selectConversation: (conversationId: string) => void;
  setComposerText: Dispatch<SetStateAction<string>>;
  setProjectName: (value: string) => void;
  settings: IncubatorChatSettings;
  setSettings: Dispatch<SetStateAction<IncubatorChatSettings>>;
  submitPrompt: (prompt: string) => Promise<void>;
  syncDraft: () => Promise<void>;
};

export function useIncubatorChatModel(
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>,
): IncubatorChatModel {
  const state = useChatState();
  const lastResetConversationIdRef = useRef<string | null>(null);
  const hasUserMessage = state.messages.some((message) => message.role === "user");
  const credentialModel = useIncubatorChatCredentialModel(
    hasUserMessage,
    state.settings,
    state.setSettings,
  );
  const conversationFingerprint = useConversationFingerprint(state.messages, state.settings);
  const draftMutation = useIncubatorDraftMutation(state.settings, state.patchConversationSession);
  const createMutation = useIncubatorCreateMutation({
    draftSetting: state.draft?.project_setting ?? null,
    onCreated: () => {
      state.createConversation();
      setFeedback(null);
    },
    projectName: state.projectName,
    setFeedback,
    settings: state.settings,
  });
  const assistantMutation = useIncubatorAssistantMutation(state.settings, state.patchConversationSession);
  const baseSubmitPrompt = useIncubatorPromptSubmit({
    activeConversationId: state.activeConversationId,
    assistantMutation,
    isResponding: assistantMutation.isPending,
    messages: state.messages,
    patchConversationSession: state.patchConversationSession,
    setFeedback,
  });
  const syncDraft = useIncubatorDraftSync({
    activeConversationId: state.activeConversationId,
    draftMutation,
    messages: state.messages,
    settings: state.settings,
  });

  useSuggestedProjectName(
    state.draft?.project_setting ?? null,
    state.hasCustomProjectName,
    state.setProjectNameState,
  );

  useEffect(() => {
    if (lastResetConversationIdRef.current === state.activeConversationId) {
      return;
    }
    lastResetConversationIdRef.current = state.activeConversationId;
    assistantMutation.reset();
    createMutation.reset();
    draftMutation.reset();
    setFeedback(null);
  }, [assistantMutation, createMutation, draftMutation, setFeedback, state.activeConversationId]);

  return {
    activeConversationId: state.activeConversationId,
    applyPromptSuggestion: (prompt: string) => state.setComposerText(prompt),
    canChat: credentialModel.canChat,
    composerText: state.composerText,
    conversationSummaries: state.conversationSummaries,
    credentialNotice: credentialModel.credentialNotice,
    credentialOptions: credentialModel.credentialOptions,
    credentialSettingsHref: credentialModel.credentialSettingsHref,
    credentialState: credentialModel.credentialState,
    createConversation: () => {
      state.createConversation();
    },
    createMutation,
    deleteConversation: state.deleteConversation,
    draft: state.draft,
    draftMutation,
    hasUserMessage,
    isConversationBusy: assistantMutation.isPending || draftMutation.isPending || createMutation.isPending,
    isCredentialLoading: credentialModel.isCredentialLoading,
    isDraftStale: isDraftStale(state.draft, state.draftFingerprint, conversationFingerprint),
    isResponding: assistantMutation.isPending,
    messages: state.messages,
    projectName: state.projectName,
    selectConversation: state.selectConversation,
    setComposerText: state.setComposerText,
    setProjectName: useProjectNameSetter(state.setHasCustomProjectName, state.setProjectNameState),
    settings: state.settings,
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
