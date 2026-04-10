"use client";

import type { DocumentTreeNode } from "@/features/studio/components/page/studio-page-support";
import type { StudioDocumentLiveSyncState } from "@/features/studio/components/document/studio-document-live-sync-support";

export type StudioDocumentEditorProps = {
  availableDocumentPaths: readonly string[];
  content: string;
  documentNode: DocumentTreeNode | null;
  documentPath: string | null;
  hasUnsavedChanges?: boolean;
  isLoading?: boolean;
  isSaving?: boolean;
  liveSyncState?: StudioDocumentLiveSyncState;
  onChange: (content: string) => void;
  onSave: () => void;
  projectId: string;
  saveNoun?: "文稿" | "文件";
};

export function isJsonStudioDocument(documentPath: string | null) {
  return Boolean(documentPath?.toLowerCase().endsWith(".json"));
}
