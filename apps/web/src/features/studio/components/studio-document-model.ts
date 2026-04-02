"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Message } from "@arco-design/web-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  buildStudioDocumentQueryKey,
  loadStudioDocument,
  resolveStudioDocumentTarget,
  saveStudioDocument,
  syncStudioDocumentQueries,
} from "@/features/studio/components/studio-document-support";

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

  const saveMutation = useMutation({
    mutationFn: (content: string) => {
      if (!documentQuery.data) {
        throw new Error("document_path_missing");
      }
      return saveStudioDocument(projectId, documentQuery.data, content);
    },
    onSuccess: (savedDocument) => {
      syncStudioDocumentQueries(queryClient, projectId, savedDocument);
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
    onError: () => {
      Message.error("保存失败，请稍后重试。");
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
