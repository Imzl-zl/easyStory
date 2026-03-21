"use client";

import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

type WorkspaceState = {
  lastProjectId: string | null;
  lastWorkflowByProject: Record<string, string>;
  setLastProjectId: (projectId: string) => void;
  setLastWorkflow: (projectId: string, workflowId: string) => void;
};

const noopStorage: StateStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      lastProjectId: null,
      lastWorkflowByProject: {},
      setLastProjectId: (projectId) => set({ lastProjectId: projectId }),
      setLastWorkflow: (projectId, workflowId) =>
        set((state) => ({
          lastProjectId: projectId,
          lastWorkflowByProject: {
            ...state.lastWorkflowByProject,
            [projectId]: workflowId,
          },
        })),
    }),
    {
      name: "easystory-workspace",
      storage: createJSONStorage(() =>
        typeof window === "undefined" ? noopStorage : localStorage,
      ),
    },
  ),
);
