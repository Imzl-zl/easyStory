"use client";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

export type StudioDocumentEditorProps = {
  availableDocumentPaths: readonly string[];
  content: string;
  documentNode: DocumentTreeNode | null;
  documentPath: string | null;
  hasUnsavedChanges?: boolean;
  isLoading?: boolean;
  isSaving?: boolean;
  onChange: (content: string) => void;
  onSave: () => void;
  projectId: string;
  saveNoun?: "文稿" | "文件";
};

export function isJsonStudioDocument(documentPath: string | null) {
  return Boolean(documentPath?.toLowerCase().endsWith(".json"));
}
