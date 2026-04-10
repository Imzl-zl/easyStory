"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Message } from "@arco-design/web-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { StudioAssistantWriteEffect } from "@/features/studio/components/chat/studio-chat-write-effects";
import { isStudioAssistantWriteSuccessStatus } from "@/features/studio/components/chat/studio-chat-write-effects";
import { resolveStudioDocumentSaveErrorMessage } from "@/features/studio/components/document/studio-document-feedback-support";
import {
  createIdleStudioDocumentLiveSyncState,
  createStaleStudioDocumentLiveSyncState,
  createSyncedStudioDocumentLiveSyncState,
  createWritingStudioDocumentLiveSyncState,
  resolveStudioDocumentBaseVersion,
  STUDIO_DOCUMENT_SYNC_SUCCESS_VISIBLE_MS,
  type StudioDocumentLiveSyncState,
} from "@/features/studio/components/document/studio-document-live-sync-support";
import {
  buildStudioDocumentQueryKey,
  type StudioLoadedDocument,
  loadStudioDocument,
  resolveStudioDocumentTarget,
  saveStudioDocument,
  syncStudioDocumentQueries,
} from "@/features/studio/components/document/studio-document-support";
import { buildStudioActiveBufferState } from "@/features/studio/components/document/studio-document-buffer-support";
import { buildStudioDocumentCatalogQueryKey } from "@/features/studio/components/document/studio-document-catalog-support";

type UseStudioDocumentModelArgs = {
  projectId: string;
  documentPath: string | null;
};

export function useStudioDocumentModel({
  projectId,
  documentPath,
}: Readonly<UseStudioDocumentModelArgs>) {
  const queryClient = useQueryClient();
  const target = resolveStudioDocumentTarget(documentPath);
  const [draftContent, setDraftContent] = useState("");
  const [dirtyPath, setDirtyPath] = useState<string | null>(null);
  const [draftBaseVersion, setDraftBaseVersion] = useState<string | null>(null);
  const [liveSyncSnapshot, setLiveSyncSnapshot] = useState<{
    path: string | null;
    state: StudioDocumentLiveSyncState;
  }>(() => ({
    path: null,
    state: createIdleStudioDocumentLiveSyncState(),
  }));
  const liveSyncState = liveSyncSnapshot.path === target?.path
    ? liveSyncSnapshot.state
    : createIdleStudioDocumentLiveSyncState();
  const liveSyncStateRef = useRef(liveSyncState);
  const targetPathRef = useRef<string | null>(null);
  const liveSyncResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const setLiveSyncStateForPath = useCallback(
    (path: string | null, state: StudioDocumentLiveSyncState) => {
      setLiveSyncSnapshot({ path, state });
    },
    [],
  );
  const dirtyPathRef = useRef<string | null>(dirtyPath);
  const hasUnsavedChangesRef = useRef(false);

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
  const currentDocumentVersion = resolveStudioDocumentBaseVersion({
    documentVersion: documentQuery.data?.version ?? "",
    draftBaseVersion,
    hasUnsavedChanges,
  });
  const documentContent = hasUnsavedChanges ? draftContent : (documentQuery.data?.content ?? "");
  const activeBufferState = resolveActiveBufferState(
    documentQuery.data,
    documentContent,
    currentDocumentVersion,
    hasUnsavedChanges,
  );

  useEffect(() => {
    hasUnsavedChangesRef.current = hasUnsavedChanges;
  }, [hasUnsavedChanges]);

  useEffect(() => {
    liveSyncStateRef.current = liveSyncState;
  }, [liveSyncState]);

  useEffect(() => {
    targetPathRef.current = target?.path ?? null;
  }, [target]);

  const clearLiveSyncResetTimer = useCallback(() => {
    if (liveSyncResetTimerRef.current !== null) {
      clearTimeout(liveSyncResetTimerRef.current);
      liveSyncResetTimerRef.current = null;
    }
  }, []);

  const resetLiveSyncState = useCallback(() => {
    clearLiveSyncResetTimer();
    setLiveSyncStateForPath(null, createIdleStudioDocumentLiveSyncState());
  }, [clearLiveSyncResetTimer, setLiveSyncStateForPath]);

  const showSyncedLiveSyncState = useCallback(() => {
    const currentPath = targetPathRef.current;
    if (!currentPath) {
      resetLiveSyncState();
      return;
    }
    clearLiveSyncResetTimer();
    setLiveSyncStateForPath(currentPath, createSyncedStudioDocumentLiveSyncState());
    liveSyncResetTimerRef.current = setTimeout(() => {
      liveSyncResetTimerRef.current = null;
      setLiveSyncStateForPath(null, createIdleStudioDocumentLiveSyncState());
    }, STUDIO_DOCUMENT_SYNC_SUCCESS_VISIBLE_MS);
  }, [clearLiveSyncResetTimer, resetLiveSyncState, setLiveSyncStateForPath]);

  useEffect(() => () => {
    clearLiveSyncResetTimer();
  }, [clearLiveSyncResetTimer]);

  const syncCurrentDocumentFromSource = useCallback(async (path: string) => {
    const syncTarget = resolveStudioDocumentTarget(path);
    if (!syncTarget) {
      return false;
    }
    const latestDocument = await loadStudioDocument(projectId, syncTarget);
    await syncStudioDocumentQueries(queryClient, projectId, latestDocument);
    void queryClient.invalidateQueries({
      queryKey: buildStudioDocumentCatalogQueryKey(projectId),
    });
    return true;
  }, [projectId, queryClient]);

  const saveMutation = useMutation({
    mutationFn: (content: string) => {
      const saveDocument = buildSaveDocumentSnapshot(
        documentQuery.data,
        currentDocumentVersion,
        hasUnsavedChanges,
      );
      if (!saveDocument) {
        throw new Error("document_path_missing");
      }
      return saveStudioDocument(projectId, saveDocument, content);
    },
    onSuccess: async (savedDocument) => {
      await syncStudioDocumentQueries(queryClient, projectId, savedDocument);
      setDraftContent((currentDraft) =>
        dirtyPathRef.current === savedDocument.path ? "" : currentDraft,
      );
      setDirtyPath((currentDirtyPath) =>
        currentDirtyPath === savedDocument.path ? null : currentDirtyPath,
      );
      setDraftBaseVersion((currentBaseVersion) =>
        dirtyPathRef.current === savedDocument.path ? null : currentBaseVersion,
      );
      resetLiveSyncState();
      Message.success(
        savedDocument.storageKind === "file" ? "已保存到项目文稿文件" : "已保存到正式文稿",
      );
    },
    onError: (error) => {
      Message.error(resolveStudioDocumentSaveErrorMessage(error));
    },
  });

  const handleContentChange = (content: string) => {
    if (!target) {
      return;
    }
    setDraftContent(content);
    setDirtyPath(target.path);
    setDraftBaseVersion((currentBaseVersion) => {
      if (dirtyPathRef.current === target.path && currentBaseVersion) {
        return currentBaseVersion;
      }
      return documentQuery.data?.version ?? currentBaseVersion;
    });
  };

  const handleSave = useCallback(() => {
    if (!target || saveMutation.isPending) {
      return;
    }
    saveMutation.mutate(documentContent);
  }, [documentContent, saveMutation, target]);

  const appendMarkdownToDocument = (markdown: string) => {
    if (!target) {
      return;
    }
    setDraftContent((currentContent) => {
      const baseContent = dirtyPath === target.path ? currentContent : (documentQuery.data?.content ?? "");
      return baseContent ? `${baseContent}\n\n${markdown}` : markdown;
    });
    setDirtyPath(target.path);
    setDraftBaseVersion((currentBaseVersion) => {
      if (dirtyPathRef.current === target.path && currentBaseVersion) {
        return currentBaseVersion;
      }
      return documentQuery.data?.version ?? currentBaseVersion;
    });
    Message.success("已追加到当前文档");
  };

  const discardUnsavedChanges = () => {
    setDraftContent("");
    setDirtyPath(null);
    setDraftBaseVersion(null);
    if (liveSyncStateRef.current.status !== "stale_remote") {
      resetLiveSyncState();
      return;
    }
    const currentPath = targetPathRef.current;
    if (!currentPath) {
      resetLiveSyncState();
      return;
    }
    void syncCurrentDocumentFromSource(currentPath)
      .then((didSync) => {
        if (!didSync || targetPathRef.current !== currentPath) {
          return;
        }
        showSyncedLiveSyncState();
      })
      .catch(() => {
        Message.error("重新加载最新文稿失败，请刷新后重试。");
      });
  };

  const handleAssistantWriteEffect = useCallback((effect: StudioAssistantWriteEffect) => {
    const currentPath = targetPathRef.current;
    if (
      isStudioAssistantWriteSuccessStatus(effect.status)
      && effect.paths.length > 0
    ) {
      void queryClient.invalidateQueries({
        queryKey: buildStudioDocumentCatalogQueryKey(projectId),
      });
      effect.paths
        .filter((path) => path !== currentPath)
        .forEach((path) => {
          void queryClient.invalidateQueries({
            queryKey: buildStudioDocumentQueryKey(projectId, path),
          });
        });
    }
    if (!currentPath || !effect.paths.includes(currentPath)) {
      return;
    }
    if (effect.status === "started") {
      clearLiveSyncResetTimer();
      setLiveSyncStateForPath(currentPath, createWritingStudioDocumentLiveSyncState());
      return;
    }
    if (!isStudioAssistantWriteSuccessStatus(effect.status)) {
      resetLiveSyncState();
      return;
    }
    if (hasUnsavedChangesRef.current) {
      clearLiveSyncResetTimer();
      setLiveSyncStateForPath(currentPath, createStaleStudioDocumentLiveSyncState());
      return;
    }
    clearLiveSyncResetTimer();
    setLiveSyncStateForPath(currentPath, createWritingStudioDocumentLiveSyncState());
    void syncCurrentDocumentFromSource(currentPath)
      .then((didSync) => {
        if (!didSync) {
          resetLiveSyncState();
          return;
        }
        if (targetPathRef.current !== currentPath) {
          return;
        }
        showSyncedLiveSyncState();
      })
      .catch(() => {
        resetLiveSyncState();
        Message.error("同步助手写入结果失败，请刷新后重试。");
      });
  }, [
    clearLiveSyncResetTimer,
    projectId,
    queryClient,
    resetLiveSyncState,
    setLiveSyncStateForPath,
    showSyncedLiveSyncState,
    syncCurrentDocumentFromSource,
  ]);

  return {
    appendMarkdownToDocument,
    activeBufferState,
    discardUnsavedChanges,
    documentContent,
    handleContentChange,
    handleAssistantWriteEffect,
    handleSave,
    hasUnsavedChanges,
    isDocumentLoading: documentQuery.isLoading && !documentQuery.data,
    isSaving: saveMutation.isPending,
    liveSyncState,
    saveNoun: documentQuery.data?.saveNoun ?? "文稿",
  };
}

function resolveActiveBufferState(
  document: StudioLoadedDocument | undefined,
  content: string,
  baseVersion: string,
  dirty: boolean,
) {
  if (!document || !baseVersion) {
    return null;
  }
  return buildStudioActiveBufferState({
    baseVersion,
    content,
    dirty,
  });
}

function buildSaveDocumentSnapshot(
  document: StudioLoadedDocument | undefined,
  baseVersion: string,
  hasUnsavedChanges: boolean,
) {
  if (!document) {
    return null;
  }
  if (!hasUnsavedChanges || document.version === baseVersion) {
    return document;
  }
  return {
    ...document,
    version: baseVersion,
  };
}
