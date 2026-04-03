"use client";

import { useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { listMyAssistantSkills, listProjectAssistantSkills } from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";

import type { StudioChatState } from "./studio-chat-state";
import {
  buildStudioChatSkillOptions,
  normalizeStudioSkillId,
  resolveStudioActiveSkillState,
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
  const skillState = useMemo(
    () => resolveStudioActiveSkillState({
      conversationSkillId: state.conversationSkillId,
      nextTurnSkillId: state.nextTurnSkillId,
      skillsLoading,
      skillOptions,
    }),
    [skillOptions, skillsLoading, state.conversationSkillId, state.nextTurnSkillId],
  );
  const skillErrorMessage = useMemo(() => {
    const skillError = projectSkillsQuery.error ?? userSkillsQuery.error;
    return skillError ? getErrorMessage(skillError) : null;
  }, [projectSkillsQuery.error, userSkillsQuery.error]);

  const patchActiveConversation = useCallback((updater: Parameters<StudioChatState["patchConversationSession"]>[1]) => {
    state.patchConversationSession(state.activeConversationId, updater);
  }, [state]);

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
