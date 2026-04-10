"use client";

export type StudioDocumentLiveSyncStatus =
  | "idle"
  | "writing"
  | "synced"
  | "stale_remote";

export type StudioDocumentLiveSyncState = {
  detail: string | null;
  status: StudioDocumentLiveSyncStatus;
};

export const STUDIO_DOCUMENT_SYNC_SUCCESS_VISIBLE_MS = 2600;

export function createIdleStudioDocumentLiveSyncState(): StudioDocumentLiveSyncState {
  return {
    detail: null,
    status: "idle",
  };
}

export function createWritingStudioDocumentLiveSyncState(): StudioDocumentLiveSyncState {
  return {
    detail: "助手正在写入当前文稿…",
    status: "writing",
  };
}

export function createSyncedStudioDocumentLiveSyncState(): StudioDocumentLiveSyncState {
  return {
    detail: "助手写入已自动同步到当前编辑器。",
    status: "synced",
  };
}

export function createStaleStudioDocumentLiveSyncState(): StudioDocumentLiveSyncState {
  return {
    detail: "远端文稿已更新，当前仍保留你的未保存草稿。",
    status: "stale_remote",
  };
}

export function resolveStudioDocumentBaseVersion(options: {
  documentVersion: string;
  draftBaseVersion: string | null;
  hasUnsavedChanges: boolean;
}) {
  if (options.hasUnsavedChanges && options.draftBaseVersion) {
    return options.draftBaseVersion;
  }
  return options.documentVersion;
}
