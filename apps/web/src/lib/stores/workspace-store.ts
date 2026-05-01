"use client";

import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

export type WorkspaceSidebarPreference = "expanded" | "collapsed";
export type StudioLeftPanelState = "expanded" | "collapsed";

type WorkspaceState = {
  clearProjectContext: () => void;
  hasHydrated: boolean;
  lastProjectId: string | null;
  lastWorkflowByProject: Record<string, string>;
  sidebarPreference: WorkspaceSidebarPreference;
  studioChatWidthByProject: Record<string, number>;
  studioLeftPanelByProject: Record<string, StudioLeftPanelState>;
  studioLeftWidthByProject: Record<string, number>;
  markHydrated: () => void;
  setLastProjectId: (projectId: string) => void;
  setSidebarPreference: (sidebarPreference: WorkspaceSidebarPreference) => void;
  setStudioChatWidth: (projectId: string, width: number | null) => void;
  setStudioLeftPanel: (projectId: string, state: StudioLeftPanelState) => void;
  setStudioLeftWidth: (projectId: string, width: number | null) => void;
  setLastWorkflow: (projectId: string, workflowId: string) => void;
};

export type PersistedWorkspaceState = Pick<
  WorkspaceState,
  "lastProjectId" | "lastWorkflowByProject" | "sidebarPreference" | "studioChatWidthByProject" | "studioLeftPanelByProject" | "studioLeftWidthByProject"
>;

const noopStorage: StateStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

export function buildWorkspacePersistedState(
  state: WorkspaceState,
): PersistedWorkspaceState {
  return {
    lastProjectId: state.lastProjectId,
    lastWorkflowByProject: state.lastWorkflowByProject,
    sidebarPreference: state.sidebarPreference,
    studioChatWidthByProject: state.studioChatWidthByProject,
    studioLeftPanelByProject: state.studioLeftPanelByProject,
    studioLeftWidthByProject: state.studioLeftWidthByProject,
  };
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      hasHydrated: false,
      lastProjectId: null,
      lastWorkflowByProject: {},
      sidebarPreference: "expanded",
      studioChatWidthByProject: {},
      studioLeftPanelByProject: {},
      studioLeftWidthByProject: {},
      clearProjectContext: () => set({ lastProjectId: null, lastWorkflowByProject: {} }),
      markHydrated: () => set({ hasHydrated: true }),
      setLastProjectId: (projectId) => set({ lastProjectId: projectId }),
      setSidebarPreference: (sidebarPreference) => set({ sidebarPreference }),
      setStudioChatWidth: (projectId, width) =>
        set((state) => {
          const nextWidths = { ...state.studioChatWidthByProject };
          if (width === null) {
            delete nextWidths[projectId];
          } else {
            nextWidths[projectId] = width;
          }
          return { studioChatWidthByProject: nextWidths };
        }),
      setStudioLeftPanel: (projectId, panelState) =>
        set((state) => ({
          studioLeftPanelByProject: {
            ...state.studioLeftPanelByProject,
            [projectId]: panelState,
          },
        })),
      setStudioLeftWidth: (projectId, width) =>
        set((state) => {
          const nextWidths = { ...state.studioLeftWidthByProject };
          if (width === null) {
            delete nextWidths[projectId];
          } else {
            nextWidths[projectId] = width;
          }
          return { studioLeftWidthByProject: nextWidths };
        }),
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
      partialize: buildWorkspacePersistedState,
      storage: createJSONStorage(() =>
        typeof window === "undefined" ? noopStorage : localStorage,
      ),
      onRehydrateStorage: () => (state) => {
        state?.markHydrated();
      },
      version: 0,
    },
  ),
);
