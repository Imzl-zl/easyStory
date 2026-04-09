"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";

import { useAuthStore } from "@/lib/stores/auth-store";

import {
  createEmptyIncubatorChatSession,
  createEmptyIncubatorChatUserState,
  normalizePersistedIncubatorChatUserState,
  readIncubatorChatUserState,
  serializeIncubatorChatUserState,
  useIncubatorChatStore,
  type IncubatorChatSession,
  type IncubatorConversationSummary,
} from "@/features/lobby/components/incubator/incubator-chat-store";

export type IncubatorChatState = {
  activeConversationId: string;
  composerText: string;
  conversationSummaries: IncubatorConversationSummary[];
  createConversation: () => string | null;
  deleteConversation: (conversationId: string) => void;
  draft: IncubatorChatSession["draft"];
  draftFingerprint: string | null;
  hasCustomProjectName: boolean;
  latestCompletedRunId: string | null;
  messages: IncubatorChatSession["messages"];
  patchConversationSession: (
    conversationId: string,
    updater: (current: IncubatorChatSession) => IncubatorChatSession,
  ) => void;
  projectName: string;
  selectConversation: (conversationId: string) => void;
  setComposerText: Dispatch<SetStateAction<string>>;
  setHasCustomProjectName: Dispatch<SetStateAction<boolean>>;
  setMessages: Dispatch<SetStateAction<IncubatorChatSession["messages"]>>;
  setProjectNameState: Dispatch<SetStateAction<string>>;
  settings: IncubatorChatSession["settings"];
  setSettings: Dispatch<SetStateAction<IncubatorChatSession["settings"]>>;
};

export function useChatState(): IncubatorChatState {
  const currentUserId = useAuthStore((state) => state.user?.userId ?? null);
  const hasStoreHydrated = useIncubatorChatStore((state) => state.hasHydrated);
  const storedUserState = useIncubatorChatStore((state) =>
    readIncubatorChatUserState(state.userStatesByUserId, currentUserId),
  );
  const createStoredConversation = useIncubatorChatStore((state) => state.createConversation);
  const deleteStoredConversation = useIncubatorChatStore((state) => state.deleteConversation);
  const ensureStoredUserState = useIncubatorChatStore((state) => state.ensureUserState);
  const patchStoredActiveConversation = useIncubatorChatStore((state) => state.patchActiveConversation);
  const patchStoredConversation = useIncubatorChatStore((state) => state.patchConversation);
  const replaceStoredUserState = useIncubatorChatStore((state) => state.replaceUserState);
  const selectStoredConversation = useIncubatorChatStore((state) => state.selectConversation);
  const emptyUserState = useMemo(() => createEmptyIncubatorChatUserState(), []);
  const restoredUserIdRef = useRef<string | null>(null);
  const conversationSummaries = useMemo<IncubatorConversationSummary[]>(() => {
    const userState = storedUserState ?? emptyUserState;
    return userState.conversations.map(({ id, title, updatedAt }) => ({ id, title, updatedAt }));
  }, [emptyUserState, storedUserState]);
  const activeConversationId = storedUserState?.activeConversationId ?? emptyUserState.activeConversationId;
  const session = useMemo(() => {
    const userState = storedUserState ?? emptyUserState;
    const activeConversation = userState.conversations.find((item) => item.id === activeConversationId)
      ?? userState.conversations[0];
    return activeConversation?.session ?? createEmptyIncubatorChatSession();
  }, [activeConversationId, emptyUserState, storedUserState]);

  useEffect(() => {
    if (!currentUserId) {
      restoredUserIdRef.current = null;
      return;
    }
    if (!hasStoreHydrated) {
      return;
    }
    ensureStoredUserState(currentUserId);
  }, [currentUserId, ensureStoredUserState, hasStoreHydrated]);

  useEffect(() => {
    if (!currentUserId) {
      restoredUserIdRef.current = null;
      return;
    }
    if (!hasStoreHydrated || restoredUserIdRef.current === currentUserId || !storedUserState) {
      return;
    }
    restoredUserIdRef.current = currentUserId;
    const normalizedUserState = normalizePersistedIncubatorChatUserState(storedUserState);
    if (serializeIncubatorChatUserState(normalizedUserState) === serializeIncubatorChatUserState(storedUserState)) {
      return;
    }
    replaceStoredUserState(currentUserId, normalizedUserState);
  }, [currentUserId, hasStoreHydrated, replaceStoredUserState, storedUserState]);

  return {
    activeConversationId,
    composerText: session.composerText,
    conversationSummaries,
    createConversation: () => currentUserId ? createStoredConversation(currentUserId) : null,
    deleteConversation: (conversationId) => {
      if (!currentUserId) {
        return;
      }
      deleteStoredConversation(currentUserId, conversationId);
    },
    draft: session.draft,
    draftFingerprint: session.draftFingerprint,
    hasCustomProjectName: session.hasCustomProjectName,
    latestCompletedRunId: session.latestCompletedRunId,
    messages: session.messages,
    patchConversationSession: (conversationId, updater) => {
      if (!currentUserId) {
        return;
      }
      patchStoredConversation(currentUserId, conversationId, updater);
    },
    projectName: session.projectName,
    selectConversation: (conversationId) => {
      if (!currentUserId) {
        return;
      }
      selectStoredConversation(currentUserId, conversationId);
    },
    setComposerText: createPersistedSessionSetter(currentUserId, patchStoredActiveConversation, "composerText"),
    setHasCustomProjectName: createPersistedSessionSetter(currentUserId, patchStoredActiveConversation, "hasCustomProjectName"),
    setMessages: createPersistedSessionSetter(currentUserId, patchStoredActiveConversation, "messages"),
    setProjectNameState: createPersistedSessionSetter(currentUserId, patchStoredActiveConversation, "projectName"),
    settings: session.settings,
    setSettings: createPersistedSessionSetter(currentUserId, patchStoredActiveConversation, "settings"),
  };
}

function createPersistedSessionSetter<K extends keyof IncubatorChatSession>(
  currentUserId: string | null,
  patchStoredActiveConversation: (
    userId: string,
    updater: (current: IncubatorChatSession) => IncubatorChatSession,
  ) => void,
  key: K,
): Dispatch<SetStateAction<IncubatorChatSession[K]>> {
  return (value) => {
    if (!currentUserId) {
      return;
    }
    patchStoredActiveConversation(currentUserId, (current) => {
      const nextValue = resolveStateValue(value, current[key]);
      if (Object.is(nextValue, current[key])) {
        return current;
      }
      return { ...current, [key]: nextValue };
    });
  };
}

function resolveStateValue<T>(value: SetStateAction<T>, current: T): T {
  return typeof value === "function"
    ? (value as (previousState: T) => T)(current)
    : value;
}
