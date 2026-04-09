"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Message } from "@arco-design/web-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { resolveStudioDocumentSaveErrorMessage } from "@/features/studio/components/document/studio-document-feedback-support";
import {
  buildStudioDocumentQueryKey,
  type StudioLoadedDocument,
  loadStudioDocument,
  resolveStudioDocumentTarget,
  saveStudioDocument,
  syncStudioDocumentQueries,
} from "@/features/studio/components/document/studio-document-support";
import { buildStudioActiveBufferState } from "@/features/studio/components/document/studio-document-buffer-support";

type UseStudioDocumentModelArgs = {
  projectId: string;
  documentPath: string | null;
};

export function useStudioDocumentModel({
  projectId,
  documentPath,
}: Readonly<UseStudioDocumentModelArgs>) {
  const queryClient = useQueryClient();
  const [draftContent, setDraftContent] = useState("");
  const [dirtyPath, setDirtyPath] = useState<string | null>(null);
  const dirtyPathRef = useRef<string | null>(dirtyPath);
  const target = resolveStudioDocumentTarget(documentPath);

  useEffect(() => {
    dirtyPathRef.current = dirtyPath;
  }, [dirtyPath]);

  const documentQuery = useQuery({
    queryKey: buildStudioDocumentQueryKey(projectId, target?.path ?? null),
    queryFn: () => {
      if (!target) {
        throw new Error("document_path_missing");
      }
      return loadStudioDocument(projectId, target);
    },
    enabled: Boolean(target),
    refetchOnWindowFocus: false,
  });

  const hasUnsavedChanges = dirtyPath !== null && dirtyPath === target?.path;
  const documentContent = hasUnsavedChanges ? draftContent : (documentQuery.data?.content ?? "");
  const activeBufferState = resolveActiveBufferState(
    documentQuery.data,
    documentContent,
    hasUnsavedChanges,
  );

  const saveMutation = useMutation({
    mutationFn: (content: string) => {
      if (!documentQuery.data) {
        throw new Error("document_path_missing");
      }
      return saveStudioDocument(projectId, documentQuery.data, content);
    },
    onSuccess: async (savedDocument) => {
      await syncStudioDocumentQueries(queryClient, projectId, savedDocument);
      setDraftContent((currentDraft) =>
        dirtyPathRef.current === savedDocument.path ? "" : currentDraft,
      );
      setDirtyPath((currentDirtyPath) =>
        currentDirtyPath === savedDocument.path ? null : currentDirtyPath,
      );
      Message.success(
        savedDocument.storageKind === "file" ? "已保存到项目文稿文件" : "已保存到正式文稿",
      );
    },
    onError: (error) => {
      Message.error(resolveStudioDocumentSaveErrorMessage(error));
    },
  });

  const handleContentChange = useCallback((content: string) => {
    if (!target) {
      return;
    }
    setDraftContent(content);
    setDirtyPath(target.path);
  }, [target]);

  const handleSave = useCallback(() => {
    if (!target || saveMutation.isPending) {
      return;
    }
    saveMutation.mutate(documentContent);
  }, [documentContent, saveMutation, target]);

  const appendMarkdownToDocument = useCallback((markdown: string) => {
    if (!target) {
      return;
    }
    setDraftContent((currentContent) => {
      const baseContent = dirtyPath === target.path ? currentContent : (documentQuery.data?.content ?? "");
      return baseContent ? `${baseContent}\n\n${markdown}` : markdown;
    });
    setDirtyPath(target.path);
    Message.success("已追加到当前文档");
  }, [dirtyPath, documentQuery.data?.content, target]);

  const discardUnsavedChanges = useCallback(() => {
    setDraftContent("");
    setDirtyPath(null);
  }, []);

  return {
    appendMarkdownToDocument,
    activeBufferState,
    discardUnsavedChanges,
    documentContent,
    handleContentChange,
    handleSave,
    hasUnsavedChanges,
    isDocumentLoading: documentQuery.isLoading || documentQuery.isFetching,
    isSaving: saveMutation.isPending,
    saveNoun: documentQuery.data?.saveNoun ?? "文稿",
  };
}

function resolveActiveBufferState(
  document: StudioLoadedDocument | undefined,
  content: string,
  dirty: boolean,
) {
  if (!document) {
    return null;
  }
  return buildStudioActiveBufferState({
    baseVersion: document.version,
    content,
    dirty,
  });
}
