"use client";

import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import {
  createConversationForUserState,
  createEmptyIncubatorChatSession,
  createEmptyIncubatorChatUserState,
  deleteConversationFromUserState,
  ensureIncubatorChatUserState,
  isIncubatorChatSessionEmpty,
  migratePersistedState,
  normalizePersistedIncubatorChatSession,
  normalizePersistedIncubatorChatUserState,
  patchConversationInUserState,
  readIncubatorActiveConversationId,
  readIncubatorChatSession,
  readIncubatorChatUserState,
  readIncubatorConversationSummaries,
  removeUserState,
  selectConversationForUserState,
  serializeIncubatorChatUserState,
  upsertUserState,
  type IncubatorChatSession,
  type IncubatorChatUserState,
  type IncubatorConversationRecord,
  type IncubatorConversationSummary,
} from "./incubator-chat-store-support";

const STORAGE_KEY = "easystory-incubator-chat";
const STORAGE_VERSION = 1;

type IncubatorChatStoreState = {
  clearSession: (userId: string) => void;
  createConversation: (userId: string) => string;
  deleteConversation: (userId: string, conversationId: string) => void;
  ensureUserState: (userId: string) => void;
  hasHydrated: boolean;
  markHydrated: () => void;
  patchActiveConversation: (
    userId: string,
    updater: (current: IncubatorChatSession) => IncubatorChatSession,
  ) => void;
  patchConversation: (
    userId: string,
    conversationId: string,
    updater: (current: IncubatorChatSession) => IncubatorChatSession,
  ) => void;
  replaceActiveConversation: (userId: string, session: IncubatorChatSession) => void;
  replaceUserState: (userId: string, userState: IncubatorChatUserState) => void;
  selectConversation: (userId: string, conversationId: string) => void;
  userStatesByUserId: Record<string, IncubatorChatUserState>;
};

const noopStorage: StateStorage = {
  getItem: () => null,
  removeItem: () => {},
  setItem: () => {},
};

export {
  createEmptyIncubatorChatSession,
  createEmptyIncubatorChatUserState,
  isIncubatorChatSessionEmpty,
  normalizePersistedIncubatorChatSession,
  normalizePersistedIncubatorChatUserState,
  readIncubatorActiveConversationId,
  readIncubatorChatSession,
  readIncubatorChatUserState,
  readIncubatorConversationSummaries,
  serializeIncubatorChatUserState,
};

export type {
  IncubatorChatSession,
  IncubatorChatUserState,
  IncubatorConversationRecord,
  IncubatorConversationSummary,
};

export function buildPersistedIncubatorChatState(state: IncubatorChatStoreState) {
  return { userStatesByUserId: state.userStatesByUserId };
}

export const useIncubatorChatStore = create<IncubatorChatStoreState>()(
  persist(
    (set) => ({
      clearSession: (userId) => set((state) => removeUserState(state.userStatesByUserId, userId)),
      createConversation: (userId) => {
        let conversationId = "";
        set((state) => {
          const currentUserState = state.userStatesByUserId[userId];
          const nextUserState = createConversationForUserState(currentUserState);
          if (nextUserState === currentUserState) {
            conversationId = currentUserState?.activeConversationId ?? "";
            return state;
          }
          conversationId = nextUserState.activeConversationId;
          return upsertUserState(state.userStatesByUserId, userId, nextUserState);
        });
        return conversationId;
      },
      deleteConversation: (userId, conversationId) =>
        set((state) => {
          const currentUserState = state.userStatesByUserId[userId];
          const nextUserState = deleteConversationFromUserState(currentUserState, conversationId);
          return nextUserState === currentUserState
            ? state
            : upsertUserState(state.userStatesByUserId, userId, nextUserState);
        }),
      ensureUserState: (userId) =>
        set((state) => {
          const currentUserState = state.userStatesByUserId[userId];
          const nextUserState = ensureIncubatorChatUserState(currentUserState);
          return currentUserState ? state : upsertUserState(state.userStatesByUserId, userId, nextUserState);
        }),
      hasHydrated: false,
      markHydrated: () => set({ hasHydrated: true }),
      patchActiveConversation: (userId, updater) =>
        set((state) => {
          const currentUserState = state.userStatesByUserId[userId];
          const nextUserState = patchConversationInUserState(currentUserState, null, updater);
          return nextUserState === currentUserState
            ? state
            : upsertUserState(state.userStatesByUserId, userId, nextUserState);
        }),
      patchConversation: (userId, conversationId, updater) =>
        set((state) => {
          const currentUserState = state.userStatesByUserId[userId];
          const nextUserState = patchConversationInUserState(currentUserState, conversationId, updater);
          return nextUserState === currentUserState
            ? state
            : upsertUserState(state.userStatesByUserId, userId, nextUserState);
        }),
      replaceActiveConversation: (userId, session) =>
        set((state) => {
          const currentUserState = state.userStatesByUserId[userId];
          const nextUserState = patchConversationInUserState(currentUserState, null, () => session);
          return nextUserState === currentUserState
            ? state
            : upsertUserState(state.userStatesByUserId, userId, nextUserState);
        }),
      replaceUserState: (userId, userState) =>
        set((state) => upsertUserState(state.userStatesByUserId, userId, userState)),
      selectConversation: (userId, conversationId) =>
        set((state) => {
          const currentUserState = state.userStatesByUserId[userId];
          const nextUserState = selectConversationForUserState(currentUserState, conversationId);
          return nextUserState === currentUserState
            ? state
            : upsertUserState(state.userStatesByUserId, userId, nextUserState);
        }),
      userStatesByUserId: {},
    }),
    {
      migrate: migratePersistedState,
      name: STORAGE_KEY,
      onRehydrateStorage: () => (state) => state?.markHydrated(),
      partialize: buildPersistedIncubatorChatState,
      storage: createJSONStorage(() => typeof window === "undefined" ? noopStorage : localStorage),
      version: STORAGE_VERSION,
    },
  ),
);
