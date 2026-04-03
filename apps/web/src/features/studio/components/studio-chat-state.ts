"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";

import { useAuthStore } from "@/lib/stores/auth-store";

import {
  buildStudioChatScopeId,
  createEmptyStudioChatProjectState,
  createEmptyStudioChatSession,
  normalizePersistedStudioChatProjectState,
  readStudioChatProjectState,
  remapDocumentPathReferencesInProjectState,
  serializeStudioChatProjectState,
  type StudioChatSession,
  type StudioConversationSummary,
} from "./studio-chat-store-support";
import { useStudioChatStore } from "./studio-chat-store";

export type StudioChatState = {
  activeConversationId: string;
  composerText: string;
  conversationSkillId: string | null;
  conversationSummaries: StudioConversationSummary[];
  createConversation: () => string | null;
  deleteConversation: (conversationId: string) => void;
  messages: StudioChatSession["messages"];
  nextTurnSkillId: string | null;
  patchConversationSession: (
    conversationId: string,
    updater: (current: StudioChatSession) => StudioChatSession,
  ) => void;
  remapDocumentPathReferences: (previousPath: string, nextPath: string | null) => void;
  selectConversation: (conversationId: string) => void;
  selectedContextPaths: string[];
  setComposerText: Dispatch<SetStateAction<string>>;
  setConversationSkillId: Dispatch<SetStateAction<string | null>>;
  setMessages: Dispatch<SetStateAction<StudioChatSession["messages"]>>;
  setNextTurnSkillId: Dispatch<SetStateAction<string | null>>;
  setSelectedContextPaths: Dispatch<SetStateAction<string[]>>;
  settings: StudioChatSession["settings"];
  setSettings: Dispatch<SetStateAction<StudioChatSession["settings"]>>;
};

export function useStudioChatState(projectId: string): StudioChatState {
  const currentUserId = useAuthStore((state) => state.user?.userId ?? null);
  const scopeId = currentUserId ? buildStudioChatScopeId(currentUserId, projectId) : null;
  const hasStoreHydrated = useStudioChatStore((state) => state.hasHydrated);
  const storedProjectState = useStudioChatStore((state) =>
    readStudioChatProjectState(state.projectStatesByScopeId, scopeId),
  );
  const createStoredConversation = useStudioChatStore((state) => state.createConversation);
  const deleteStoredConversation = useStudioChatStore((state) => state.deleteConversation);
  const ensureStoredProjectState = useStudioChatStore((state) => state.ensureProjectState);
  const patchStoredActiveConversation = useStudioChatStore((state) => state.patchActiveConversation);
  const patchStoredConversation = useStudioChatStore((state) => state.patchConversation);
  const replaceStoredProjectState = useStudioChatStore((state) => state.replaceProjectState);
  const selectStoredConversation = useStudioChatStore((state) => state.selectConversation);
  const emptyProjectState = useMemo(() => createEmptyStudioChatProjectState(), []);
  const restoredScopeIdRef = useRef<string | null>(null);
  const conversationSummaries = useMemo(() => {
    const projectState = storedProjectState ?? emptyProjectState;
    return projectState.conversations.map(({ id, title, updatedAt }) => ({ id, title, updatedAt }));
  }, [emptyProjectState, storedProjectState]);
  const activeConversationId = storedProjectState?.activeConversationId ?? emptyProjectState.activeConversationId;
  const session = useMemo(() => {
    const projectState = storedProjectState ?? emptyProjectState;
    const activeConversation = projectState.conversations.find((item) => item.id === activeConversationId)
      ?? projectState.conversations[0];
    return activeConversation?.session ?? createEmptyStudioChatSession();
  }, [activeConversationId, emptyProjectState, storedProjectState]);
  const setComposerText = useMemo(
    () => createSessionSetter(scopeId, patchStoredActiveConversation, "composerText"),
    [patchStoredActiveConversation, scopeId],
  );
  const setConversationSkillId = useMemo(
    () => createSessionSetter(scopeId, patchStoredActiveConversation, "conversationSkillId"),
    [patchStoredActiveConversation, scopeId],
  );
  const setMessages = useMemo(
    () => createSessionSetter(scopeId, patchStoredActiveConversation, "messages"),
    [patchStoredActiveConversation, scopeId],
  );
  const setNextTurnSkillId = useMemo(
    () => createSessionSetter(scopeId, patchStoredActiveConversation, "nextTurnSkillId"),
    [patchStoredActiveConversation, scopeId],
  );
  const setSelectedContextPaths = useMemo(
    () => createSessionSetter(scopeId, patchStoredActiveConversation, "selectedContextPaths"),
    [patchStoredActiveConversation, scopeId],
  );
  const setSettings = useMemo(
    () => createSessionSetter(scopeId, patchStoredActiveConversation, "settings"),
    [patchStoredActiveConversation, scopeId],
  );
  const createConversation = useCallback(
    () => (scopeId ? createStoredConversation(scopeId) : null),
    [createStoredConversation, scopeId],
  );
  const deleteConversation = useCallback((conversationId: string) => {
    if (!scopeId) {
      return;
    }
    deleteStoredConversation(scopeId, conversationId);
  }, [deleteStoredConversation, scopeId]);
  const patchConversationSession = useCallback((conversationId: string, updater: (current: StudioChatSession) => StudioChatSession) => {
    if (!scopeId) {
      return;
    }
    patchStoredConversation(scopeId, conversationId, updater);
  }, [patchStoredConversation, scopeId]);
  const remapDocumentPathReferences = useCallback((previousPath: string, nextPath: string | null) => {
    if (!scopeId || !storedProjectState) {
      return;
    }
    const nextProjectState = remapDocumentPathReferencesInProjectState(
      storedProjectState,
      previousPath,
      nextPath,
    );
    if (nextProjectState === storedProjectState) {
      return;
    }
    replaceStoredProjectState(scopeId, nextProjectState);
  }, [replaceStoredProjectState, scopeId, storedProjectState]);
  const selectConversation = useCallback((conversationId: string) => {
    if (!scopeId) {
      return;
    }
    selectStoredConversation(scopeId, conversationId);
  }, [scopeId, selectStoredConversation]);

  useEffect(() => {
    if (!scopeId) {
      restoredScopeIdRef.current = null;
      return;
    }
    if (!hasStoreHydrated) {
      return;
    }
    ensureStoredProjectState(scopeId);
  }, [ensureStoredProjectState, hasStoreHydrated, scopeId]);

  useEffect(() => {
    if (!scopeId) {
      restoredScopeIdRef.current = null;
      return;
    }
    if (!hasStoreHydrated || restoredScopeIdRef.current === scopeId || !storedProjectState) {
      return;
    }
    restoredScopeIdRef.current = scopeId;
    const normalizedProjectState = normalizePersistedStudioChatProjectState(storedProjectState);
    if (serializeStudioChatProjectState(normalizedProjectState) === serializeStudioChatProjectState(storedProjectState)) {
      return;
    }
    replaceStoredProjectState(scopeId, normalizedProjectState);
  }, [hasStoreHydrated, replaceStoredProjectState, scopeId, storedProjectState]);

  return {
    activeConversationId,
    composerText: session.composerText,
    conversationSkillId: session.conversationSkillId,
    conversationSummaries,
    createConversation,
    deleteConversation,
    messages: session.messages,
    nextTurnSkillId: session.nextTurnSkillId,
    patchConversationSession,
    remapDocumentPathReferences,
    selectConversation,
    selectedContextPaths: session.selectedContextPaths,
    setComposerText,
    setConversationSkillId,
    setMessages,
    setNextTurnSkillId,
    setSelectedContextPaths,
    settings: session.settings,
    setSettings,
  };
}

function createSessionSetter<K extends keyof StudioChatSession>(
  scopeId: string | null,
  patchStoredActiveConversation: (
    scopeId: string,
    updater: (current: StudioChatSession) => StudioChatSession,
  ) => void,
  key: K,
): Dispatch<SetStateAction<StudioChatSession[K]>> {
  return (value) => {
    if (!scopeId) {
      return;
    }
    patchStoredActiveConversation(scopeId, (current) => {
      const nextValue = resolveStateValue(value, current[key]);
      if (Object.is(nextValue, current[key])) {
        return current;
      }
      return { ...current, [key]: nextValue };
    });
  };
}

function resolveStateValue<T>(value: SetStateAction<T>, current: T): T {
  return typeof value === "function" ? (value as (previous: T) => T)(current) : value;
}
