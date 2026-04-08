"use client";

import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import {
  createConversationForProjectState,
  ensureStudioChatProjectState,
  normalizePersistedStudioChatProjectState,
  patchConversationInProjectState,
  selectConversationForProjectState,
  upsertProjectState,
  type StudioConversationPatchOptions,
  type StudioChatProjectState,
  type StudioChatSession,
  deleteConversationFromProjectState,
} from "./studio-chat-store-support";

const STORAGE_KEY = "easystory-studio-chat";
const STORAGE_VERSION = 2;

type StudioChatStoreState = {
  createConversation: (scopeId: string) => string;
  deleteConversation: (scopeId: string, conversationId: string) => void;
  ensureProjectState: (scopeId: string) => void;
  hasHydrated: boolean;
  markHydrated: () => void;
  patchActiveConversation: (
    scopeId: string,
    updater: (current: StudioChatSession) => StudioChatSession,
    options?: StudioConversationPatchOptions,
  ) => void;
  patchConversation: (
    scopeId: string,
    conversationId: string,
    updater: (current: StudioChatSession) => StudioChatSession,
    options?: StudioConversationPatchOptions,
  ) => void;
  projectStatesByScopeId: Record<string, StudioChatProjectState>;
  replaceProjectState: (scopeId: string, projectState: StudioChatProjectState) => void;
  selectConversation: (scopeId: string, conversationId: string) => void;
};

const noopStorage: StateStorage = {
  getItem: () => null,
  removeItem: () => {},
  setItem: () => {},
};

export function buildPersistedStudioChatState(state: StudioChatStoreState) {
  return { projectStatesByScopeId: state.projectStatesByScopeId };
}

export const useStudioChatStore = create<StudioChatStoreState>()(
  persist(
    (set) => ({
      createConversation: (scopeId) => {
        let conversationId = "";
        set((state) => {
          const currentProjectState = state.projectStatesByScopeId[scopeId];
          const nextProjectState = createConversationForProjectState(currentProjectState);
          conversationId = nextProjectState.activeConversationId;
          return upsertProjectState(state.projectStatesByScopeId, scopeId, nextProjectState);
        });
        return conversationId;
      },
      deleteConversation: (scopeId, conversationId) =>
        set((state) =>
          upsertProjectState(
            state.projectStatesByScopeId,
            scopeId,
            deleteConversationFromProjectState(state.projectStatesByScopeId[scopeId], conversationId),
          )),
      ensureProjectState: (scopeId) =>
        set((state) => {
          if (state.projectStatesByScopeId[scopeId]) {
            return state;
          }
          return upsertProjectState(
            state.projectStatesByScopeId,
            scopeId,
            ensureStudioChatProjectState(undefined),
          );
        }),
      hasHydrated: false,
      markHydrated: () => set({ hasHydrated: true }),
      patchActiveConversation: (scopeId, updater, options) =>
        set((state) =>
          upsertProjectState(
            state.projectStatesByScopeId,
            scopeId,
            patchConversationInProjectState(state.projectStatesByScopeId[scopeId], null, updater, options),
          )),
      patchConversation: (scopeId, conversationId, updater, options) =>
        set((state) =>
          upsertProjectState(
            state.projectStatesByScopeId,
            scopeId,
            patchConversationInProjectState(
              state.projectStatesByScopeId[scopeId],
              conversationId,
              updater,
              options,
            ),
          )),
      projectStatesByScopeId: {},
      replaceProjectState: (scopeId, projectState) =>
        set((state) => upsertProjectState(state.projectStatesByScopeId, scopeId, projectState)),
      selectConversation: (scopeId, conversationId) =>
        set((state) =>
          upsertProjectState(
            state.projectStatesByScopeId,
            scopeId,
            selectConversationForProjectState(state.projectStatesByScopeId[scopeId], conversationId),
          )),
    }),
    {
      migrate: (persistedState) => {
        const state = persistedState as { projectStatesByScopeId?: Record<string, unknown> } | undefined;
        return {
          projectStatesByScopeId: Object.fromEntries(
            Object.entries(state?.projectStatesByScopeId ?? {}).map(([scopeId, projectState]) => [
              scopeId,
              normalizePersistedStudioChatProjectState(projectState),
            ]),
          ),
        };
      },
      name: STORAGE_KEY,
      onRehydrateStorage: () => (state) => state?.markHydrated(),
      partialize: buildPersistedStudioChatState,
      storage: createJSONStorage(() => (typeof window === "undefined" ? noopStorage : localStorage)),
      version: STORAGE_VERSION,
    },
  ),
);
