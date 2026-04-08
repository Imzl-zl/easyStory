"use client";

import { useCallback, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { listMyAssistantSkills, listProjectAssistantSkills } from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";

import type { StudioChatState } from "./studio-chat-state";
import type { StudioConversationPatchOptions } from "./studio-chat-store-support";
import {
  buildStudioChatSkillOptions,
  normalizeStudioSkillId,
  normalizeStudioSkillSelection,
  resolveStudioActiveSkillState,
  type StudioSkillLookupStatus,
  resolveStudioUsableSkillSelection,
} from "./studio-chat-skill-support";

export type StudioChatSkillModel = {
  clearConversationSkill: () => void;
  clearNextTurnSkill: () => void;
  resetToPlainChat: () => void;
  skillErrorMessage: string | null;
  skillOptions: ReturnType<typeof buildStudioChatSkillOptions>;
  skillState: ReturnType<typeof resolveStudioActiveSkillState>;
  skillsLoading: boolean;
  useSkillForConversation: (skillId: string) => void;
  useSkillOnce: (skillId: string) => void;
};

export function useStudioChatSkillModel(
  projectId: string,
  state: Pick<
    StudioChatState,
    "activeConversationId"
    | "conversationSkillId"
    | "nextTurnSkillId"
    | "patchConversationSession"
  >,
): StudioChatSkillModel {
  const {
    activeConversationId,
    conversationSkillId,
    nextTurnSkillId,
    patchConversationSession,
  } = state;
  const projectSkillsQuery = useQuery({
    queryKey: ["assistant-skills", "project", projectId, "studio-chat"],
    queryFn: () => listProjectAssistantSkills(projectId),
  });
  const userSkillsQuery = useQuery({
    queryKey: ["assistant-skills", "user", "studio-chat"],
    queryFn: listMyAssistantSkills,
  });
  const skillOptions = useMemo(
    () => buildStudioChatSkillOptions({
      projectSkills: projectSkillsQuery.data,
      userSkills: userSkillsQuery.data,
    }),
    [projectSkillsQuery.data, userSkillsQuery.data],
  );
  const skillsLoading = projectSkillsQuery.isLoading || userSkillsQuery.isLoading;
  const skillErrorMessage = useMemo(() => {
    const skillError = projectSkillsQuery.error ?? userSkillsQuery.error;
    return skillError ? getErrorMessage(skillError) : null;
  }, [projectSkillsQuery.error, userSkillsQuery.error]);
  const skillLookupStatus = useMemo<StudioSkillLookupStatus>(() => {
    if (skillsLoading) {
      return "loading";
    }
    return skillErrorMessage ? "error" : "ready";
  }, [skillErrorMessage, skillsLoading]);
  const skillState = useMemo(
    () => resolveStudioActiveSkillState({
      conversationSkillId,
      nextTurnSkillId,
      skillLookupStatus,
      skillsLoading,
      skillOptions,
    }),
    [conversationSkillId, nextTurnSkillId, skillLookupStatus, skillOptions, skillsLoading],
  );
  const skillLookupReady = skillLookupStatus === "ready";
  const normalizedSelection = useMemo(
    () => normalizeStudioSkillSelection({
      conversationSkillId,
      nextTurnSkillId,
    }),
    [conversationSkillId, nextTurnSkillId],
  );
  const usableSkillSelection = useMemo(
    () => resolveStudioUsableSkillSelection({
      conversationSkillId,
      nextTurnSkillId,
      skillLookupReady,
      skillOptions,
    }),
    [
      conversationSkillId,
      nextTurnSkillId,
      skillLookupReady,
      skillOptions,
    ],
  );

  const patchActiveConversation = useCallback((
    updater: Parameters<StudioChatState["patchConversationSession"]>[1],
    options?: StudioConversationPatchOptions,
  ) => {
    patchConversationSession(activeConversationId, updater, options);
  }, [activeConversationId, patchConversationSession]);

  useEffect(() => {
    if (!skillLookupReady) {
      return;
    }
    if (
      usableSkillSelection.conversationSkillId === normalizedSelection.conversationSkillId
      && usableSkillSelection.nextTurnSkillId === normalizedSelection.nextTurnSkillId
    ) {
      return;
    }
    patchActiveConversation((current) => {
      const currentSelection = normalizeStudioSkillSelection({
        conversationSkillId: current.conversationSkillId,
        nextTurnSkillId: current.nextTurnSkillId,
      });
      if (
        usableSkillSelection.conversationSkillId === currentSelection.conversationSkillId
        && usableSkillSelection.nextTurnSkillId === currentSelection.nextTurnSkillId
      ) {
        return current;
      }
      return {
        ...current,
        conversationSkillId: usableSkillSelection.conversationSkillId,
        nextTurnSkillId: usableSkillSelection.nextTurnSkillId,
      };
    }, { preserveUpdatedAt: true });
  }, [
    normalizedSelection.conversationSkillId,
    normalizedSelection.nextTurnSkillId,
    patchActiveConversation,
    skillLookupReady,
    usableSkillSelection.conversationSkillId,
    usableSkillSelection.nextTurnSkillId,
  ]);

  const useSkillForConversation = useCallback((skillId: string) => {
    const normalizedSkillId = normalizeStudioSkillId(skillId);
    patchActiveConversation((current) => ({
      ...current,
      conversationSkillId: normalizedSkillId,
      nextTurnSkillId: null,
    }));
  }, [patchActiveConversation]);

  const useSkillOnce = useCallback((skillId: string) => {
    const normalizedSkillId = normalizeStudioSkillId(skillId);
    patchActiveConversation((current) => ({
      ...current,
      nextTurnSkillId:
        normalizedSkillId && normalizedSkillId !== current.conversationSkillId
          ? normalizedSkillId
          : null,
    }));
  }, [patchActiveConversation]);

  const clearConversationSkill = useCallback(() => {
    patchActiveConversation((current) => (
      current.conversationSkillId
        ? { ...current, conversationSkillId: null }
        : current
    ));
  }, [patchActiveConversation]);

  const clearNextTurnSkill = useCallback(() => {
    patchActiveConversation((current) => (
      current.nextTurnSkillId
        ? { ...current, nextTurnSkillId: null }
        : current
    ));
  }, [patchActiveConversation]);

  const resetToPlainChat = useCallback(() => {
    patchActiveConversation((current) => (
      current.conversationSkillId || current.nextTurnSkillId
        ? { ...current, conversationSkillId: null, nextTurnSkillId: null }
        : current
    ));
  }, [patchActiveConversation]);

  return {
    clearConversationSkill,
    clearNextTurnSkill,
    resetToPlainChat,
    skillErrorMessage,
    skillOptions,
    skillState,
    skillsLoading,
    useSkillForConversation,
    useSkillOnce,
  };
}
