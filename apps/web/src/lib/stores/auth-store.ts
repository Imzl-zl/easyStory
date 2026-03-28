"use client";

import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import type { AuthToken } from "@/lib/api/types";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

type AuthUser = {
  userId: string;
  username: string;
};

type AuthState = {
  hasHydrated: boolean;
  token: string | null;
  user: AuthUser | null;
  setSession: (session: AuthToken) => void;
  clearSession: () => void;
  markHydrated: () => void;
};

const noopStorage: StateStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      hasHydrated: false,
      token: null,
      user: null,
      setSession: (session) =>
        set({
          token: session.access_token,
          user: {
            userId: session.user_id,
            username: session.username,
          },
        }),
      clearSession: () => {
        useWorkspaceStore.getState().clearProjectContext();
        set({ token: null, user: null });
      },
      markHydrated: () => set({ hasHydrated: true }),
    }),
    {
      name: "easystory-auth",
      storage: createJSONStorage(() =>
        typeof window === "undefined" ? noopStorage : localStorage,
      ),
      onRehydrateStorage: () => (state) => {
        state?.markHydrated();
      },
    },
  ),
);

export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}
