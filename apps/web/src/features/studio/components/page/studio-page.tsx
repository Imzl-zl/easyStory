"use client";

import { useEffect, useMemo, useTransition, useCallback, useState, useRef } from "react";
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Message } from "@arco-design/web-react";

import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import { DocumentTree } from "@/features/studio/components/tree/document-tree";
import { StudioDocumentEditor } from "@/features/studio/components/document/studio-document-editor";
import { StudioDocumentTreeDialog } from "@/features/studio/components/tree/studio-document-tree-dialog";
import { AiChatPanel } from "@/features/studio/components/chat/ai-chat-panel";
import { useStudioDocumentModel } from "@/features/studio/components/document/studio-document-model";
import { useStudioChatModel } from "@/features/studio/components/chat/studio-chat-model";
import { buildStudioDocumentCatalogQueryKey } from "@/features/studio/components/document/studio-document-catalog-support";
import {
  buildStudioDocumentEntryPath,
  buildStudioDocumentTree,
  buildStudioPathWithParams,
  buildStudioChatGridTemplateColumns,
  clampStudioChatSidebarWidth,
  findClosestRemainingFilePath,
  findNodeByPath,
  findFirstFilePath,
  getStudioPanelLabel,
  isStudioDesktopLayout,
  isDocumentTreePathAffected,
  listDocumentTreeFilePaths,
  listStaleChapters,
  readStudioDocumentEntryBaseName,
  remapDocumentTreePath,
  resolveDefaultStudioChatSidebarWidth,
  resolveStudioChatLayoutMode,
  resolveStudioChatSidebarBounds,
  STUDIO_CHAT_RESIZE_STEP,
  resolveDefaultDocumentPathFromPanel,
  resolveStudioDocumentPath,
  resolveStudioPanel,
} from "@/features/studio/components/page/studio-page-support";
import { listChapters } from "@/lib/api/content";
import {
  createProjectDocumentEntry,
  deleteProjectDocumentEntry,
  getProject,
  listProjectDocumentTree,
  renameProjectDocumentEntry,
} from "@/lib/api/projects";
import { getErrorMessage } from "@/lib/api/client";
import { useUnsavedChangesGuard } from "@/lib/hooks/use-unsaved-changes-guard";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";
import type { DocumentTreeNode } from "@/features/studio/components/page/studio-page-support";

type StudioPageProps = {
  projectId: string;
};

const STUDIO_TOOLBAR_BUTTON_CLASS = "ink-button-secondary whitespace-nowrap";
const STUDIO_SAVE_BUTTON_CLASS =
  "ink-button whitespace-nowrap h-9 px-4 text-[13px] shadow-md";
const STUDIO_STALE_BADGE_CLASS =
  "inline-flex items-center gap-2 h-7 px-3 rounded-pill border border-accent-primary-muted bg-accent-soft text-[0.72rem] font-medium tracking-[0.08em] text-accent-primary";
const STUDIO_STALE_BADGE_DOT_CLASS =
  "inline-flex h-1.5 w-1.5 rounded-full bg-accent-tertiary ring-2 ring-accent-primary-muted";
const STUDIO_GRID_WITH_CHAT_CLASS =
  "grid [grid-template-columns:1fr] lg:[grid-template-columns:236px_minmax(0,1fr)_minmax(392px,0.72fr)] xl:[grid-template-columns:244px_minmax(0,1fr)_minmax(408px,0.76fr)] [grid-template-rows:auto_minmax(0,1fr)] h-full min-h-0 bg-canvas relative overflow-hidden";
const STUDIO_GRID_WITHOUT_CHAT_CLASS =
  "grid [grid-template-columns:1fr] lg:[grid-template-columns:236px_minmax(0,1fr)] [grid-template-rows:auto_minmax(0,1fr)] h-full min-h-0 bg-canvas relative overflow-hidden";

type DocumentTreeDialogState =
  | { mode: "create-file" | "create-folder"; parentPath: string; parentLabel: string }
  | { mode: "rename"; node: DocumentTreeNode }
  | { mode: "delete"; node: DocumentTreeNode }
  | null;

export function StudioPage({ projectId }: StudioPageProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [, startTransition] = useTransition();
  const [documentTreeDialog, setDocumentTreeDialog] = useState<DocumentTreeDialogState>(null);
  const [documentTreeDialogValue, setDocumentTreeDialogValue] = useState("");
  const [dragChatWidth, setDragChatWidth] = useState<number | null>(null);
  const [measuredChatWidth, setMeasuredChatWidth] = useState(0);
  const [studioGridWidth, setStudioGridWidth] = useState(0);
  const studioGridRef = useRef<HTMLDivElement>(null);
  const chatPanelRef = useRef<HTMLElement>(null);
  const currentSearch = searchParams.toString();
  const currentUrl = currentSearch ? `${pathname}?${currentSearch}` : pathname;

  const rawDocumentPath = searchParams.get("doc");
  const rawPanel = searchParams.get("panel");
  const rawChapter = searchParams.get("chapter");
  const chatOpen = searchParams.get("chat") !== "0";
  const storedChatWidth = useWorkspaceStore((state) => state.studioChatWidthByProject[projectId] ?? null);
  const setStoredChatWidth = useWorkspaceStore((state) => state.setStudioChatWidth);

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const chaptersQuery = useQuery({
    queryKey: ["chapters", projectId],
    queryFn: () => listChapters(projectId),
  });

  const projectDocumentTreeQuery = useQuery({
    queryKey: ["project-document-tree", projectId],
    queryFn: () => listProjectDocumentTree(projectId),
  });

  const documentTree = useMemo(() => {
    return buildStudioDocumentTree(chaptersQuery.data ?? [], projectDocumentTreeQuery.data);
  }, [chaptersQuery.data, projectDocumentTreeQuery.data]);

  const fallbackDocumentPath = useMemo(() => {
    const panelDocumentPath = resolveDefaultDocumentPathFromPanel(rawPanel, chaptersQuery.data, rawChapter);
    if (panelDocumentPath) {
      return panelDocumentPath;
    }
    if (rawPanel) {
      return null;
    }
    if (!projectDocumentTreeQuery.data) {
      return null;
    }
    return findFirstFilePath(documentTree);
  }, [chaptersQuery.data, documentTree, projectDocumentTreeQuery.data, rawChapter, rawPanel]);

  const rawDocumentNode = useMemo(() => {
    if (!rawDocumentPath) {
      return null;
    }
    return findNodeByPath(documentTree, rawDocumentPath);
  }, [documentTree, rawDocumentPath]);
  const documentPath = useMemo(
    () => resolveStudioDocumentPath(rawDocumentPath, documentTree, Boolean(projectDocumentTreeQuery.data), fallbackDocumentPath),
    [documentTree, fallbackDocumentPath, projectDocumentTreeQuery.data, rawDocumentPath],
  );
  const documentPathSelectionSignal = useMemo(
    () => Symbol(documentPath ?? "__studio-empty-document__"),
    [documentPath],
  );

  const selectedNode = useMemo(() => {
    if (!documentPath) {
      return null;
    }
    return findNodeByPath(documentTree, documentPath);
  }, [documentTree, documentPath]);
  const availableDocumentPaths = useMemo(() => listDocumentTreeFilePaths(documentTree), [documentTree]);

  const staleChapters = useMemo(() => listStaleChapters(chaptersQuery.data), [chaptersQuery.data]);
  const projectName = projectQuery.data?.name ?? "正在加载项目…";
  const activePanel = resolveStudioPanel(rawPanel);
  const activePanelLabel = getStudioPanelLabel(activePanel);
  const headerSectionLabel = documentPath?.split("/")[0] ?? (rawPanel ? activePanelLabel : "创作台");
  const headerMeta = selectedNode
    ? `${projectName} · ${documentPath}`
    : rawPanel === "chapter"
      ? `${projectName} · 当前还没有可直接打开的章节文稿`
      : fallbackDocumentPath
        ? `${projectName} · 已切到 ${activePanelLabel} 默认文稿`
        : `${projectName} · 从左侧目录选择文稿开始编辑`;
  const documentModel = useStudioDocumentModel({
    projectId,
    documentPath,
  });
  const navigationGuard = useUnsavedChangesGuard({
    currentUrl,
    isDirty: documentModel.hasUnsavedChanges,
    router,
  });
  const chatModel = useStudioChatModel({
    activeBufferState: documentModel.activeBufferState,
    currentDocumentPath: documentPath,
    onWriteEffect: documentModel.handleAssistantWriteEffect,
    projectId,
  });

  const updateParams = useCallback((patches: Record<string, string | null>) => {
    startTransition(() => {
      router.replace(buildStudioPathWithParams(pathname, currentSearch, patches));
    });
  }, [currentSearch, pathname, router, startTransition]);

  useEffect(() => {
    if (!rawDocumentPath || !projectDocumentTreeQuery.data || rawDocumentNode) {
      return;
    }
    Message.warning("目标文稿不存在，已切回可用文稿。");
    updateParams({ doc: fallbackDocumentPath });
  }, [fallbackDocumentPath, projectDocumentTreeQuery.data, rawDocumentNode, rawDocumentPath, updateParams]);

  const closeDocumentTreeDialog = useCallback(() => {
    setDocumentTreeDialog(null);
    setDocumentTreeDialogValue("");
  }, []);

  const invalidateProjectDocumentQueries = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["project-document-tree", projectId] });
    await queryClient.invalidateQueries({ queryKey: buildStudioDocumentCatalogQueryKey(projectId) });
  }, [projectId, queryClient]);

  const createDocumentEntryMutation = useMutation({
    mutationFn: (payload: { kind: "file" | "folder"; path: string }) =>
      createProjectDocumentEntry(projectId, payload),
    onSuccess: async (entry) => {
      await invalidateProjectDocumentQueries();
      closeDocumentTreeDialog();
      Message.success(entry.node_type === "file" ? "已新建文稿" : "已新建目录");
      if (entry.node_type !== "file") {
        return;
      }
      navigationGuard.attemptNavigation(() => {
        documentModel.discardUnsavedChanges();
        updateParams({ doc: entry.path });
      });
    },
    onError: (error) => {
      Message.error(getErrorMessage(error));
    },
  });

  const renameDocumentEntryMutation = useMutation({
    mutationFn: (payload: { path: string; next_path: string }) =>
      renameProjectDocumentEntry(projectId, payload),
    onSuccess: async (entry, payload) => {
      const nextDocumentPath = documentPath
        ? remapDocumentTreePath(documentPath, payload.path, entry.path)
        : null;
      await invalidateProjectDocumentQueries();
      closeDocumentTreeDialog();
      chatModel.remapDocumentPathReferences(payload.path, entry.path);
      if (nextDocumentPath !== documentPath) {
        documentModel.discardUnsavedChanges();
        updateParams({ doc: nextDocumentPath });
      }
      Message.success(entry.node_type === "file" ? "已重命名文稿" : "已重命名目录");
    },
    onError: (error) => {
      Message.error(getErrorMessage(error));
    },
  });

  const deleteDocumentEntryMutation = useMutation({
    mutationFn: (path: string) => deleteProjectDocumentEntry(projectId, path),
    onSuccess: async (entry) => {
      const currentDocumentAffected = documentPath
        ? isDocumentTreePathAffected(documentPath, entry.path)
        : false;
      const nextDocumentPath = currentDocumentAffected
        ? findClosestRemainingFilePath(documentTree, entry.path, documentPath)
        : documentPath;
      await invalidateProjectDocumentQueries();
      closeDocumentTreeDialog();
      chatModel.remapDocumentPathReferences(entry.path, null);
      if (currentDocumentAffected) {
        documentModel.discardUnsavedChanges();
        updateParams({ doc: nextDocumentPath });
      }
      Message.success(entry.node_type === "file" ? "已删除文稿" : "已删除目录");
    },
    onError: (error) => {
      Message.error(getErrorMessage(error));
    },
  });

  const handleSelectNode = useCallback((node: DocumentTreeNode) => {
    if (node.type !== "file" || node.path === documentPath) {
      return;
    }
    navigationGuard.attemptNavigation(() => {
      documentModel.discardUnsavedChanges();
      updateParams({ doc: node.path });
    });
  }, [documentModel, documentPath, navigationGuard, updateParams]);

  const handleCopyMarkdown = useCallback((markdown: string) => {
    void copyMarkdownToClipboard(markdown);
  }, []);

  const handleAddDocument = useCallback((parentPath: string) => {
    setDocumentTreeDialog({
      mode: "create-file",
      parentPath,
      parentLabel: readDocumentTreeLabel(parentPath),
    });
    setDocumentTreeDialogValue("");
  }, []);

  const handleAddFolder = useCallback((parentPath: string) => {
    setDocumentTreeDialog({
      mode: "create-folder",
      parentPath,
      parentLabel: readDocumentTreeLabel(parentPath),
    });
    setDocumentTreeDialogValue("");
  }, []);

  const handleRenameNode = useCallback((node: DocumentTreeNode) => {
    setDocumentTreeDialog({ mode: "rename", node });
    setDocumentTreeDialogValue(readStudioDocumentEntryBaseName(node));
  }, []);

  const handleDeleteNode = useCallback((node: DocumentTreeNode) => {
    setDocumentTreeDialog({ mode: "delete", node });
    setDocumentTreeDialogValue("");
  }, []);

  const handleConfirmDocumentTreeDialog = useCallback(() => {
    if (!documentTreeDialog) {
      return;
    }
    if (documentTreeDialog.mode === "create-file" || documentTreeDialog.mode === "create-folder") {
      const kind = documentTreeDialog.mode === "create-file" ? "file" : "folder";
      const path = buildStudioDocumentEntryPath(
        documentTreeDialog.parentPath,
        documentTreeDialogValue,
        kind,
      );
      if (!path) {
        Message.warning(readInvalidDocumentEntryNameMessage(kind, documentTreeDialog.parentPath));
        return;
      }
      createDocumentEntryMutation.mutate({ kind, path });
      return;
    }
    if (documentTreeDialog.mode !== "rename" && documentTreeDialog.mode !== "delete") {
      return;
    }
    const targetNode = documentTreeDialog.node;

    if (
      documentPath
      && documentModel.hasUnsavedChanges
      && isDocumentTreePathAffected(documentPath, targetNode.path)
    ) {
      Message.warning("当前文稿有未保存修改，先保存或放弃后，再重命名或删除相关文稿。");
      return;
    }

    if (documentTreeDialog.mode === "rename") {
      const nextPath = buildStudioDocumentEntryPath(
        readDocumentTreeParentPath(targetNode.path),
        documentTreeDialogValue,
        targetNode.type,
      );
      if (!nextPath) {
        Message.warning(
          readInvalidDocumentEntryNameMessage(
            targetNode.type,
            readDocumentTreeParentPath(targetNode.path),
          ),
        );
        return;
      }
      if (nextPath === targetNode.path) {
        Message.warning("名称没有变化。");
        return;
      }
      renameDocumentEntryMutation.mutate({
        path: targetNode.path,
        next_path: nextPath,
      });
      return;
    }

    deleteDocumentEntryMutation.mutate(targetNode.path);
  }, [
    createDocumentEntryMutation,
    deleteDocumentEntryMutation,
    documentModel,
    documentPath,
    documentTreeDialog,
    documentTreeDialogValue,
    renameDocumentEntryMutation,
  ]);

  const handleCreateNewDocument = useCallback(() => {
    Message.info("先在左侧创作结构里新建文稿，再把内容整理到当前写作流里。");
  }, []);

  const toggleChat = useCallback(() => {
    updateParams({ chat: chatOpen ? "0" : null });
  }, [chatOpen, updateParams]);
  const saveButtonLabel = !documentPath
    ? "先选择文稿"
    : documentModel.isDocumentLoading
      ? "载入中…"
      : documentModel.isSaving
        ? "保存中…"
        : documentModel.hasUnsavedChanges
          ? `保存${documentModel.saveNoun}`
          : `${documentModel.saveNoun}已保存`;
  const saveButtonClass = documentModel.hasUnsavedChanges
    ? STUDIO_SAVE_BUTTON_CLASS
    : `${STUDIO_TOOLBAR_BUTTON_CLASS} h-9 px-4 text-[13px]`;
  const studioGridClassName = chatOpen ? STUDIO_GRID_WITH_CHAT_CLASS : STUDIO_GRID_WITHOUT_CHAT_CLASS;
  const effectiveChatWidth = dragChatWidth ?? storedChatWidth;
  const resolvedDesktopChatWidth = useMemo(() => {
    if (!chatOpen || !isStudioDesktopLayout(studioGridWidth) || studioGridWidth <= 0) {
      return null;
    }
    if (effectiveChatWidth === null) {
      if (measuredChatWidth > 0) {
        return clampStudioChatSidebarWidth(measuredChatWidth, studioGridWidth);
      }
      return resolveDefaultStudioChatSidebarWidth(studioGridWidth);
    }
    return clampStudioChatSidebarWidth(effectiveChatWidth, studioGridWidth);
  }, [chatOpen, effectiveChatWidth, measuredChatWidth, studioGridWidth]);
  const studioGridStyle = useMemo<CSSProperties | undefined>(() => {
    const gridTemplateColumns = buildStudioChatGridTemplateColumns({
      chatOpen,
      chatWidth: effectiveChatWidth,
      containerWidth: studioGridWidth,
    });
    return gridTemplateColumns ? { gridTemplateColumns } : undefined;
  }, [chatOpen, effectiveChatWidth, studioGridWidth]);
  const chatLayoutMode = resolveStudioChatLayoutMode(resolvedDesktopChatWidth ?? measuredChatWidth);
  const documentTreeDialogCopy = buildDocumentTreeDialogCopy(documentTreeDialog);
  const documentTreeDialogPending = documentTreeDialog?.mode === "rename"
    ? renameDocumentEntryMutation.isPending
    : documentTreeDialog?.mode === "delete"
      ? deleteDocumentEntryMutation.isPending
      : createDocumentEntryMutation.isPending;

  useEffect(() => {
    const gridNode = studioGridRef.current;
    if (!gridNode) {
      return;
    }
    const updateMeasurements = () => {
      const nextWidth = Math.round(gridNode.getBoundingClientRect().width);
      setStudioGridWidth((current) => (current === nextWidth ? current : nextWidth));
      const nextChatWidth = chatPanelRef.current
        ? Math.round(chatPanelRef.current.getBoundingClientRect().width)
        : 0;
      setMeasuredChatWidth((current) => (current === nextChatWidth ? current : nextChatWidth));
    };
    updateMeasurements();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(() => updateMeasurements());
      observer.observe(gridNode);
      if (chatPanelRef.current) {
        observer.observe(chatPanelRef.current);
      }
      return () => observer.disconnect();
    }
    window.addEventListener("resize", updateMeasurements);
    return () => window.removeEventListener("resize", updateMeasurements);
  }, [chatOpen]);

  useEffect(() => {
    if (!chatOpen && dragChatWidth !== null) {
      setDragChatWidth(null);
    }
  }, [chatOpen, dragChatWidth]);

  useEffect(() => {
    if (
      !chatOpen
      || dragChatWidth !== null
      || storedChatWidth === null
      || !isStudioDesktopLayout(studioGridWidth)
      || studioGridWidth <= 0
    ) {
      return;
    }
    const clampedWidth = clampStudioChatSidebarWidth(storedChatWidth, studioGridWidth);
    if (clampedWidth !== storedChatWidth) {
      setStoredChatWidth(projectId, clampedWidth);
    }
  }, [chatOpen, dragChatWidth, projectId, setStoredChatWidth, storedChatWidth, studioGridWidth]);

  const handleChatResizePointerDown = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (!chatOpen || !isStudioDesktopLayout(studioGridWidth)) {
      return;
    }
    const gridElement = studioGridRef.current;
    if (!gridElement) {
      return;
    }
    event.preventDefault();
    const pointerId = event.pointerId;
    const startWidth = resolvedDesktopChatWidth ?? resolveDefaultStudioChatSidebarWidth(studioGridWidth);
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;

    const resolveWidthFromPointer = (clientX: number) => {
      const rect = gridElement.getBoundingClientRect();
      return clampStudioChatSidebarWidth(rect.right - clientX, rect.width);
    };

    const cleanup = () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerCancel);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };

    const handlePointerMove = (moveEvent: PointerEvent) => {
      if (moveEvent.pointerId !== pointerId) {
        return;
      }
      setDragChatWidth(resolveWidthFromPointer(moveEvent.clientX));
    };

    const handlePointerUp = (upEvent: PointerEvent) => {
      if (upEvent.pointerId !== pointerId) {
        return;
      }
      cleanup();
      setDragChatWidth(null);
      setStoredChatWidth(projectId, resolveWidthFromPointer(upEvent.clientX));
    };

    const handlePointerCancel = (cancelEvent: PointerEvent) => {
      if (cancelEvent.pointerId !== pointerId) {
        return;
      }
      cleanup();
      setDragChatWidth(null);
    };

    setDragChatWidth(startWidth);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerCancel);
  }, [chatOpen, projectId, resolvedDesktopChatWidth, setStoredChatWidth, studioGridWidth]);

  const handleChatResizeKeyDown = useCallback((event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (!chatOpen || !isStudioDesktopLayout(studioGridWidth) || studioGridWidth <= 0) {
      return;
    }
    const currentWidth = resolvedDesktopChatWidth ?? resolveDefaultStudioChatSidebarWidth(studioGridWidth);
    const bounds = resolveStudioChatSidebarBounds(studioGridWidth);

    let nextWidth: number | null = null;
    if (event.key === "ArrowLeft") {
      nextWidth = clampStudioChatSidebarWidth(currentWidth + STUDIO_CHAT_RESIZE_STEP, studioGridWidth);
    } else if (event.key === "ArrowRight") {
      nextWidth = clampStudioChatSidebarWidth(currentWidth - STUDIO_CHAT_RESIZE_STEP, studioGridWidth);
    } else if (event.key === "Home") {
      nextWidth = bounds.min;
    } else if (event.key === "End") {
      nextWidth = bounds.max;
    }

    if (nextWidth === null) {
      return;
    }
    event.preventDefault();
    setStoredChatWidth(projectId, nextWidth);
  }, [chatOpen, projectId, resolvedDesktopChatWidth, setStoredChatWidth, studioGridWidth]);

  return (
    <>
      <div className={studioGridClassName} ref={studioGridRef} style={studioGridStyle}>
        <div className="fixed -top-1/2 -right-[20%] w-full h-[150%] pointer-events-none [background:radial-gradient(ellipse_at_60%_40%,rgba(124,110,93,0.05)_0%,transparent_50%),radial-gradient(ellipse_at_30%_70%,rgba(196,167,125,0.04)_0%,transparent_40%)]" />

        <div className="col-span-full flex flex-wrap items-center justify-between gap-3 px-4 py-2 bg-glass-heavy backdrop-blur-xl border-b border-line-soft relative z-10 animate-[inkFadeIn_0.4s_cubic-bezier(0.16,1,0.3,1)] lg:px-5">
          <h1 className="sr-only">{selectedNode?.label ?? "创作工作台"}</h1>
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="inline-flex shrink-0 items-center rounded-pill border border-accent-primary-muted bg-accent-soft px-3 py-1 text-[0.7rem] font-semibold tracking-[0.12em] uppercase text-accent-primary">
              {headerSectionLabel}
            </span>
            <p className="m-0 truncate text-[0.78rem] text-text-secondary">{headerMeta}</p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              className={saveButtonClass}
              disabled={!documentPath || documentModel.isDocumentLoading || documentModel.isSaving || !documentModel.hasUnsavedChanges}
              onClick={documentModel.handleSave}
              type="button"
            >
              {saveButtonLabel}
            </button>
            <button className={`${STUDIO_TOOLBAR_BUTTON_CLASS} h-9 px-4 text-[13px]`} type="button" onClick={toggleChat}>
              {chatOpen ? "收起助手" : "展开助手"}
            </button>
            <button
              className={`${STUDIO_TOOLBAR_BUTTON_CLASS} h-9 px-4 text-[13px]`}
              type="button"
              onClick={() =>
                navigationGuard.attemptNavigation(() => {
                  router.push(`/workspace/project/${projectId}/engine`);
                })
              }
            >
              作品推进
            </button>
            {staleChapters.length > 0 ? (
              <span className={STUDIO_STALE_BADGE_CLASS}>
                <span aria-hidden="true" className={STUDIO_STALE_BADGE_DOT_CLASS} />
                {staleChapters.length} 个章节待整理
              </span>
            ) : null}
          </div>
        </div>

        <>
          <aside className="relative z-5 flex min-h-0 flex-col overflow-hidden bg-glass-heavy backdrop-blur-md shadow-panel-side animate-[slideFromLeft_0.5s_cubic-bezier(0.16,1,0.3,1)]">
            <div className="absolute top-0 right-0 w-0.5 h-full bg-gradient-to-b from-transparent via-accent-primary to-transparent opacity-15" />
            <DocumentTree
              selectedPath={documentPath}
              selectedPathSignal={documentPathSelectionSignal}
              tree={documentTree}
              onAddDocument={handleAddDocument}
              onAddFolder={handleAddFolder}
              onDeleteNode={handleDeleteNode}
              onRenameNode={handleRenameNode}
              onSelectNode={handleSelectNode}
            />
          </aside>

          <main className="relative z-1 flex min-h-0 flex-col overflow-hidden bg-surface shadow-lg animate-[inkFadeIn_0.6s_cubic-bezier(0.16,1,0.3,1)]">
            <div className="absolute inset-0 border-x border-line-soft pointer-events-none" />
            <StudioDocumentEditor
              availableDocumentPaths={availableDocumentPaths}
              documentPath={documentPath}
              documentNode={selectedNode}
              content={documentModel.documentContent}
              isLoading={documentModel.isDocumentLoading}
              liveSyncState={documentModel.liveSyncState}
              isSaving={documentModel.isSaving}
              saveNoun={documentModel.saveNoun}
              onChange={documentModel.handleContentChange}
              onSave={documentModel.handleSave}
              hasUnsavedChanges={documentModel.hasUnsavedChanges}
              projectId={projectId}
            />
          </main>

          {chatOpen ? (
            <aside className="relative z-5 flex min-h-0 min-w-0 flex-col overflow-hidden bg-glass-heavy backdrop-blur-md border-l border-line-soft shadow-panel-side animate-[slideFromRight_0.5s_cubic-bezier(0.16,1,0.3,1)]" ref={chatPanelRef}>
              {resolvedDesktopChatWidth !== null ? (
                <div
                  aria-label="调整共创助手宽度"
                  aria-orientation="vertical"
                  aria-valuemax={resolveStudioChatSidebarBounds(studioGridWidth).max}
                  aria-valuemin={resolveStudioChatSidebarBounds(studioGridWidth).min}
                  aria-valuenow={resolvedDesktopChatWidth}
                  className="absolute inset-y-0 left-0 z-20 hidden w-4 -translate-x-1/2 cursor-col-resize select-none items-center justify-center lg:flex"
                  role="separator"
                  tabIndex={0}
                  title="拖动或使用方向键调整共创助手宽度；Home 到最窄，End 到最宽"
                  onKeyDown={handleChatResizeKeyDown}
                  onPointerDown={handleChatResizePointerDown}
                >
                  <div className={`flex h-24 w-2 items-center justify-center rounded-full border border-line-soft bg-glass-heavy shadow-glass transition ${dragChatWidth === null ? "opacity-0 hover:opacity-100 focus-within:opacity-100 focus-visible:opacity-100" : "opacity-100"}`}>
                    <div className="h-10 w-[3px] rounded-full bg-accent-primary/55" />
                  </div>
                </div>
              ) : null}
              <div className="absolute top-0 left-0 w-0.5 h-full bg-gradient-to-b from-transparent via-accent-tertiary to-transparent opacity-20" />
              <AiChatPanel
                activeConversationId={chatModel.activeConversationId}
                attachments={chatModel.attachments}
                availableContexts={documentTree}
                canChat={chatModel.credentialModel.canChat}
                layoutMode={chatLayoutMode}
                composerText={chatModel.composerText}
                conversationSummaries={chatModel.conversationSummaries}
                createConversation={chatModel.createConversation}
                credentialNotice={chatModel.credentialModel.credentialNotice}
                credentialSettingsHref={chatModel.credentialModel.credentialSettingsHref}
                credentialState={chatModel.credentialModel.credentialState}
                currentDocumentPath={documentPath}
                deleteConversation={chatModel.deleteConversation}
                isCredentialLoading={chatModel.credentialModel.isCredentialLoading}
                isResponding={chatModel.isResponding}
                messages={chatModel.messages}
                onCopyMarkdown={handleCopyMarkdown}
                onAppendToDocument={documentModel.appendMarkdownToDocument}
                onAttachFiles={chatModel.handleAttachFiles}
                onComposerTextChange={chatModel.setComposerText}
                onCreateNewDocument={handleCreateNewDocument}
                onModelNameChange={chatModel.handleModelNameChange}
                onProviderChange={chatModel.handleProviderChange}
                onReasoningEffortChange={chatModel.handleReasoningEffortChange}
                onRemoveAttachment={chatModel.handleRemoveAttachment}
                onSendMessage={chatModel.handleSendMessage}
                onStreamOutputChange={chatModel.handleStreamOutputChange}
                onThinkingBudgetChange={chatModel.handleThinkingBudgetChange}
                onThinkingLevelChange={chatModel.handleThinkingLevelChange}
                onToggleContext={chatModel.handleToggleContext}
                onToggleWriteToCurrentDocument={chatModel.handleToggleWriteToCurrentDocument}
                providerOptions={chatModel.credentialModel.providerOptions}
                selectConversation={chatModel.selectConversation}
                selectedContextPaths={chatModel.selectedContextPaths}
                selectedCredentialApiDialect={chatModel.credentialModel.selectedCredential?.apiDialect ?? null}
                selectedCredentialLabel={chatModel.selectedCredentialLabel}
                settings={chatModel.settings}
                showWriteToCurrentDocument={chatModel.showWriteToCurrentDocument}
                skillModel={chatModel.skillModel}
                visibleModelLabel={chatModel.visibleModelLabel}
                writeIntentNotice={chatModel.writeIntentNotice}
                writeTargetDisabledReason={chatModel.writeTargetDisabledReason}
                isWriteToCurrentDocumentEnabled={chatModel.isWriteToCurrentDocumentEnabled}
              />
            </aside>
          ) : null}
        </>
      </div>
      <UnsavedChangesDialog
        isOpen={navigationGuard.isConfirmOpen}
        isPending={false}
        onClose={navigationGuard.handleDialogClose}
        onConfirm={navigationGuard.handleDialogConfirm}
      />
      <StudioDocumentTreeDialog
        confirmLoading={documentTreeDialogPending}
        description={documentTreeDialogCopy?.description ?? ""}
        nameValue={documentTreeDialogValue}
        okText={documentTreeDialogCopy?.okText ?? "确定"}
        open={documentTreeDialog !== null}
        title={documentTreeDialogCopy?.title ?? "管理文稿"}
        onCancel={closeDocumentTreeDialog}
        onConfirm={handleConfirmDocumentTreeDialog}
        onNameChange={documentTreeDialogCopy?.requiresName ? setDocumentTreeDialogValue : undefined}
      />
    </>
  );
}

function buildDocumentTreeDialogCopy(dialog: DocumentTreeDialogState): {
  description: string;
  okText: string;
  requiresName: boolean;
  title: string;
} | null {
  if (!dialog) {
    return null;
  }
  if (dialog.mode === "create-file") {
    return {
      description: readCreateDocumentDescription(dialog.parentPath),
      okText: isContentDocumentParentPath(dialog.parentPath) ? "新建章节" : "新建文稿",
      requiresName: true,
      title: isContentDocumentParentPath(dialog.parentPath) ? "新建章节" : "新建文稿",
    };
  }
  if (dialog.mode === "create-folder") {
    return {
      description: isContentDocumentParentPath(dialog.parentPath)
        ? `在“${dialog.parentLabel}”下新建卷目录或正文分组。`
        : `在“${dialog.parentLabel}”下新建一个自定义目录。`,
      okText: "新建目录",
      requiresName: true,
      title: "新建目录",
    };
  }
  if (dialog.mode === "rename") {
    return {
      description: `修改“${dialog.node.label}”的名称。`,
      okText: "确认重命名",
      requiresName: true,
      title: dialog.node.type === "file" ? "重命名文稿" : "重命名目录",
    };
  }
  return dialog.mode === "delete"
    ? {
      description: dialog.node.type === "file"
        ? `删除“${dialog.node.label}”后，这份自定义文稿将从项目文稿树中移除。`
        : `删除“${dialog.node.label}”后，这个目录和其中的自定义文稿都会一起移除。`,
      okText: "确认删除",
      requiresName: false,
      title: dialog.node.type === "file" ? "删除文稿" : "删除目录",
    }
    : null;
}

function readDocumentTreeParentPath(path: string) {
  return path.split("/").slice(0, -1).join("/");
}

function readDocumentTreeLabel(path: string) {
  if (!path) {
    return "根目录";
  }
  return path.split("/").at(-1) ?? path;
}

function readInvalidDocumentEntryNameMessage(kind: "file" | "folder", parentPath = "") {
  if (kind === "file") {
    if (isContentDocumentParentPath(parentPath)) {
      return "章节号不能为空，且只能输入类似 1、001 或 第1章。";
    }
    return "文稿名不能为空，不能包含斜杠；默认创建 .md，输入 .json 会保留为 JSON 文件。";
  }
  return "目录名不能为空，不能包含斜杠，也不能以 .md 或 .json 结尾。";
}

function readCreateDocumentDescription(parentPath: string) {
  if (isContentDocumentParentPath(parentPath)) {
    return `在“${readDocumentTreeLabel(parentPath)}”下新建章节文稿，输入章节号即可，例如 1 或第1章。`;
  }
  return `在“${readDocumentTreeLabel(parentPath)}”下新建一份文稿文件；默认是 .md，输入 .json 会直接创建 JSON。`;
}

function isContentDocumentParentPath(path: string) {
  return path === "正文" || path.startsWith("正文/");
}

async function copyMarkdownToClipboard(markdown: string) {
  try {
    await navigator.clipboard.writeText(markdown);
    Message.success("已复制到剪贴板");
  } catch {
    Message.error("复制失败，请检查浏览器剪贴板权限后重试。");
  }
}
