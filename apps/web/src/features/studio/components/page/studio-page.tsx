"use client";

import { useEffect, useMemo, useTransition, useCallback, useState, useRef } from "react";
import type { CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Message } from "@arco-design/web-react";

import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import { DocumentTree } from "@/features/studio/components/tree/document-tree";
import { StudioDocumentEditor } from "@/features/studio/components/document/studio-document-editor";
import { StudioDocumentTreeDialog } from "@/features/studio/components/tree/studio-document-tree-dialog";
import { AiChatPanel } from "@/features/studio/components/chat/ai-chat-panel";
import { useStudioDocumentModel } from "@/features/studio/components/document/studio-document-model";
import { useStudioChatModel } from "@/features/studio/components/chat/studio-chat-model";
import {
  buildStudioDocumentTree,
  buildStudioLeftPanelGridTemplateColumns,
  clampStudioChatSidebarWidth,
  copyMarkdownToClipboard,
  findFirstFilePath,
  findNodeByPath,
  getStudioPanelLabel,
  isStudioDesktopLayout,
  listDocumentTreeFilePaths,
  listStaleChapters,
  resolveDefaultStudioChatSidebarWidth,
  resolveLeftPanelWidth,
  resolveStudioChatLayoutMode,
  resolveStudioChatSidebarBounds,
  resolveStudioDocumentPath,
  resolveStudioLeftPanelBounds,
  resolveStudioPanel,
  resolveDefaultDocumentPathFromPanel,
  buildStudioPathWithParams,
} from "@/features/studio/components/page/studio-page-support";
import { useChatPanelResize, useLeftPanelResize } from "@/features/studio/components/page/use-studio-panel-resize";
import { useStudioDocumentTreeActions } from "@/features/studio/components/page/use-studio-document-tree-actions";
import { AnalysisIcon, ExportIcon, SaveIcon, SidebarExpandIcon, SparkleIcon, WorkflowIcon } from "@/features/studio/components/page/studio-page-icons";
import { listChapters } from "@/lib/api/content";
import { getProject, listProjectDocumentTree } from "@/lib/api/projects";
import { useUnsavedChangesGuard } from "@/lib/hooks/use-unsaved-changes-guard";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

type StudioPageProps = {
  projectId: string;
};

export function StudioPage({ projectId }: StudioPageProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();
  const [measuredChatWidth, setMeasuredChatWidth] = useState(0);
  const [studioGridWidth, setStudioGridWidth] = useState(0);
  const [mounted, setMounted] = useState(false);
  const studioGridRef = useRef<HTMLDivElement>(null);
  const chatPanelRef = useRef<HTMLElement>(null);
  const currentSearch = searchParams.toString();
  const currentUrl = currentSearch ? `${pathname}?${currentSearch}` : pathname;

  const rawDocumentPath = searchParams.get("doc");
  const rawPanel = searchParams.get("panel");
  const rawChapter = searchParams.get("chapter");
  const chatOpen = searchParams.get("chat") !== "0";
  const storedChatWidth = useWorkspaceStore((s) => s.studioChatWidthByProject[projectId] ?? null);
  const setStoredChatWidth = useWorkspaceStore((s) => s.setStudioChatWidth);
  const storedLeftPanel = useWorkspaceStore((s) => s.studioLeftPanelByProject[projectId] ?? "expanded");
  const setStoredLeftPanel = useWorkspaceStore((s) => s.setStudioLeftPanel);
  const storedLeftWidth = useWorkspaceStore((s) => s.studioLeftWidthByProject[projectId] ?? null);
  const setStoredLeftWidth = useWorkspaceStore((s) => s.setStudioLeftWidth);
  const leftCollapsed = storedLeftPanel === "collapsed";

  useEffect(() => { queueMicrotask(() => setMounted(true)); }, []);

  const projectQuery = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId) });
  const chaptersQuery = useQuery({ queryKey: ["chapters", projectId], queryFn: () => listChapters(projectId) });
  const projectDocumentTreeQuery = useQuery({
    queryKey: ["project-document-tree", projectId],
    queryFn: () => listProjectDocumentTree(projectId),
  });

  const documentTree = useMemo(
    () => buildStudioDocumentTree(chaptersQuery.data ?? [], projectDocumentTreeQuery.data),
    [chaptersQuery.data, projectDocumentTreeQuery.data],
  );
  const fallbackDocumentPath = useMemo(() => {
    const panelPath = resolveDefaultDocumentPathFromPanel(rawPanel, chaptersQuery.data, rawChapter);
    if (panelPath) return panelPath;
    if (rawPanel || !projectDocumentTreeQuery.data) return null;
    return findFirstFilePath(documentTree);
  }, [chaptersQuery.data, documentTree, projectDocumentTreeQuery.data, rawChapter, rawPanel]);

  const rawDocumentNode = useMemo(
    () => rawDocumentPath ? findNodeByPath(documentTree, rawDocumentPath) : null,
    [documentTree, rawDocumentPath],
  );
  const documentPath = useMemo(
    () => resolveStudioDocumentPath(rawDocumentPath, documentTree, Boolean(projectDocumentTreeQuery.data), fallbackDocumentPath),
    [documentTree, fallbackDocumentPath, projectDocumentTreeQuery.data, rawDocumentPath],
  );
  const documentPathSelectionSignal = useMemo(
    () => Symbol(documentPath ?? "__studio-empty-document__"),
    [documentPath],
  );
  const selectedNode = useMemo(
    () => documentPath ? findNodeByPath(documentTree, documentPath) : null,
    [documentTree, documentPath],
  );
  const availableDocumentPaths = useMemo(() => listDocumentTreeFilePaths(documentTree), [documentTree]);
  const staleChapters = useMemo(() => listStaleChapters(chaptersQuery.data), [chaptersQuery.data]);
  const projectName = projectQuery.data?.name ?? "正在加载项目…";
  const activePanel = resolveStudioPanel(rawPanel);
  const activePanelLabel = getStudioPanelLabel(activePanel);
  const headerSectionLabel = documentPath?.split("/")[0] ?? (rawPanel ? activePanelLabel : "创作台");

  const documentModel = useStudioDocumentModel({ projectId, documentPath });
  const navigationGuard = useUnsavedChangesGuard({ currentUrl, isDirty: documentModel.hasUnsavedChanges, router });
  const chatModel = useStudioChatModel({
    activeBufferState: documentModel.activeBufferState,
    currentDocumentPath: documentPath,
    onWriteEffect: documentModel.handleAssistantWriteEffect,
    projectId,
  });

  const updateParams = useCallback((patches: Record<string, string | null>) => {
    startTransition(() => { router.replace(buildStudioPathWithParams(pathname, currentSearch, patches)); });
  }, [currentSearch, pathname, router, startTransition]);

  useEffect(() => {
    if (!rawDocumentPath || !projectDocumentTreeQuery.data || rawDocumentNode) return;
    Message.warning("目标文稿不存在，已切回可用文稿。");
    updateParams({ doc: fallbackDocumentPath });
  }, [fallbackDocumentPath, projectDocumentTreeQuery.data, rawDocumentNode, rawDocumentPath, updateParams]);

  const treeActions = useStudioDocumentTreeActions({
    chatModel,
    documentModel,
    documentPath,
    navigationGuard,
    projectId,
    tree: documentTree,
    updateParams,
  });

  const toggleChat = useCallback(() => { updateParams({ chat: chatOpen ? "0" : null }); }, [chatOpen, updateParams]);
  const toggleLeftPanel = useCallback(() => {
    setStoredLeftPanel(projectId, leftCollapsed ? "expanded" : "collapsed");
  }, [leftCollapsed, projectId, setStoredLeftPanel]);

  const resolvedChatWidthRef = useRef<number | null>(null);

  const chatResize = useChatPanelResize({
    chatOpen, effectiveLeftWidth: storedLeftWidth, gridRef: studioGridRef, leftCollapsed,
    projectId, resolvedDesktopChatWidth: resolvedChatWidthRef.current, setStoredChatWidth, studioGridWidth,
  });
  const leftResize = useLeftPanelResize({
    effectiveLeftWidth: storedLeftWidth, gridRef: studioGridRef, leftCollapsed,
    projectId, setStoredLeftWidth, studioGridWidth,
  });

  const effectiveChatWidth = chatResize.dragWidth ?? storedChatWidth;
  const effectiveLeftWidth = leftResize.dragWidth ?? storedLeftWidth;

  const resolvedDesktopChatWidth = useMemo(() => {
    if (!chatOpen || !isStudioDesktopLayout(studioGridWidth) || studioGridWidth <= 0) return null;
    if (effectiveChatWidth === null) {
      return measuredChatWidth > 0
        ? clampStudioChatSidebarWidth(measuredChatWidth, studioGridWidth)
        : resolveDefaultStudioChatSidebarWidth(studioGridWidth);
    }
    return clampStudioChatSidebarWidth(effectiveChatWidth, studioGridWidth);
  }, [chatOpen, effectiveChatWidth, measuredChatWidth, studioGridWidth]);
  resolvedChatWidthRef.current = resolvedDesktopChatWidth;

  const studioGridStyle = useMemo<CSSProperties | undefined>(() => {
    const chatWidthForGrid = chatOpen ? (resolvedDesktopChatWidth ?? effectiveChatWidth) : null;
    const gridTemplateColumns = buildStudioLeftPanelGridTemplateColumns({
      chatOpen, chatWidth: chatWidthForGrid, containerWidth: studioGridWidth, leftCollapsed, customLeftWidth: effectiveLeftWidth,
    });
    return gridTemplateColumns ? { gridTemplateColumns } : undefined;
  }, [chatOpen, effectiveChatWidth, effectiveLeftWidth, resolvedDesktopChatWidth, studioGridWidth, leftCollapsed]);

  const chatLayoutMode = resolveStudioChatLayoutMode(resolvedDesktopChatWidth ?? measuredChatWidth);

  useEffect(() => {
    const gridNode = studioGridRef.current;
    if (!gridNode) return;
    const updateMeasurements = () => {
      const nextWidth = Math.round(gridNode.getBoundingClientRect().width);
      setStudioGridWidth((c) => (c === nextWidth ? c : nextWidth));
      const nextChatWidth = chatPanelRef.current
        ? Math.round(chatPanelRef.current.getBoundingClientRect().width) : 0;
      setMeasuredChatWidth((c) => (c === nextChatWidth ? c : nextChatWidth));
    };
    updateMeasurements();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(() => updateMeasurements());
      observer.observe(gridNode);
      if (chatPanelRef.current) observer.observe(chatPanelRef.current);
      return () => observer.disconnect();
    }
    window.addEventListener("resize", updateMeasurements);
    return () => window.removeEventListener("resize", updateMeasurements);
  }, [chatOpen]);

  useEffect(() => {
    if (!chatOpen && chatResize.dragWidth !== null) {
      chatResize.resetDrag();
    }
  }, [chatOpen, chatResize]);

  useEffect(() => {
    if (!chatOpen || chatResize.dragWidth !== null || storedChatWidth === null
      || !isStudioDesktopLayout(studioGridWidth) || studioGridWidth <= 0) return;
    const clampedWidth = clampStudioChatSidebarWidth(storedChatWidth, studioGridWidth);
    if (clampedWidth !== storedChatWidth) setStoredChatWidth(projectId, clampedWidth);
  }, [chatOpen, chatResize.dragWidth, projectId, setStoredChatWidth, storedChatWidth, studioGridWidth]);

  const saveButtonLabel = !documentPath
    ? "先选择文稿"
    : documentModel.isDocumentLoading
      ? "载入中…"
      : documentModel.isSaving
        ? "保存中…"
        : documentModel.hasUnsavedChanges
          ? `保存${documentModel.saveNoun}`
          : `${documentModel.saveNoun}已保存`;

  return (
    <>
      <div
        className="studio-grid"
        ref={studioGridRef}
        style={studioGridStyle}
        data-chat-open={chatOpen}
        data-left-collapsed={leftCollapsed || undefined}
        data-mounted={mounted}
      >
        <header className="studio-topbar">
          <div className="studio-topbar__left">
            <div className="studio-topbar__project-info">
              <span className="studio-topbar__section">{headerSectionLabel}</span>
              <span className="studio-topbar__project-name">{projectName}</span>
            </div>
            {staleChapters.length > 0 ? (
              <span className="studio-topbar__stale-badge" title="点击查看待整理章节">
                <span className="studio-topbar__stale-dot" />
                {staleChapters.length} 待整理
              </span>
            ) : null}
          </div>
          <div className="studio-topbar__right">
            <button
              className={`studio-topbar-btn ${documentModel.hasUnsavedChanges ? "studio-topbar-btn--primary" : ""}`}
              disabled={!documentPath || documentModel.isDocumentLoading || documentModel.isSaving || !documentModel.hasUnsavedChanges}
              onClick={documentModel.handleSave}
              type="button"
              title={saveButtonLabel}
            >
              <SaveIcon />
              <span className="hidden sm:inline">{saveButtonLabel}</span>
            </button>
            <span className="studio-topbar__divider" />
            <Link
              className="studio-topbar-btn"
              href={`/workspace/project/${projectId}/engine`}
              title="跳转工作流引擎"
            >
              <WorkflowIcon />
              <span className="hidden sm:inline">工作流</span>
            </Link>
            <Link
              className="studio-topbar-btn"
              href={`/workspace/project/${projectId}/lab`}
              title="跳转分析实验室"
            >
              <AnalysisIcon />
              <span className="hidden sm:inline">分析</span>
            </Link>
            <button
              className="studio-topbar-btn studio-topbar-btn--icon"
              type="button"
              title="导出"
              onClick={() => Message.info("导出功能即将上线")}
            >
              <ExportIcon />
            </button>
            <button
              className={`studio-topbar-btn ${chatOpen ? "studio-topbar-btn--active" : ""}`}
              type="button"
              onClick={toggleChat}
              title={chatOpen ? "收起助手" : "打开助手"}
            >
              <SparkleIcon />
              <span className="hidden sm:inline">{chatOpen ? "收起" : "助手"}</span>
            </button>
          </div>
        </header>

        <aside className={`studio-sidebar studio-sidebar--left ${leftCollapsed ? "studio-sidebar--left-collapsed" : ""}`}>
          {leftCollapsed ? (
            <div className="studio-sidebar__collapsed-rail">
              <button className="studio-sidebar__toggle-btn" onClick={toggleLeftPanel} title="展开目录" type="button">
                <SidebarExpandIcon />
              </button>
            </div>
          ) : (
            <DocumentTree
              selectedPath={documentPath}
              selectedPathSignal={documentPathSelectionSignal}
              tree={documentTree}
              onAddDocument={treeActions.handleAddDocument}
              onAddFolder={treeActions.handleAddFolder}
              onDeleteNode={treeActions.handleDeleteNode}
              onRenameNode={treeActions.handleRenameNode}
              onSelectNode={treeActions.handleSelectNode}
              onCollapse={toggleLeftPanel}
            />
          )}
          {!leftCollapsed && isStudioDesktopLayout(studioGridWidth) ? (
            <div
              aria-label="调整目录宽度"
              aria-orientation="vertical"
              aria-valuemax={resolveStudioLeftPanelBounds(studioGridWidth).max}
              aria-valuemin={resolveStudioLeftPanelBounds(studioGridWidth).min}
              aria-valuenow={resolveLeftPanelWidth(studioGridWidth, false, effectiveLeftWidth)}
              className="studio-resizer studio-resizer--left"
              role="separator"
              tabIndex={0}
              title="拖动或使用方向键调整目录宽度；Home 到最窄，End 到最宽"
              onKeyDown={leftResize.handleKeyDown}
              onPointerDown={leftResize.handlePointerDown}
            >
              <div className={`studio-resizer__handle ${leftResize.dragWidth !== null ? "studio-resizer__handle--dragging" : ""}`}>
                <div className="studio-resizer__line" />
              </div>
            </div>
          ) : null}
        </aside>

        <main className="studio-editor-wrap">
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
          <aside className="studio-sidebar studio-sidebar--right" ref={chatPanelRef}>
            {resolvedDesktopChatWidth !== null ? (
              <div
                aria-label="调整共创助手宽度"
                aria-orientation="vertical"
                aria-valuemax={resolveStudioChatSidebarBounds(studioGridWidth, resolveLeftPanelWidth(studioGridWidth, leftCollapsed, effectiveLeftWidth)).max}
                aria-valuemin={resolveStudioChatSidebarBounds(studioGridWidth, resolveLeftPanelWidth(studioGridWidth, leftCollapsed, effectiveLeftWidth)).min}
                aria-valuenow={resolvedDesktopChatWidth}
                className="studio-resizer"
                role="separator"
                tabIndex={0}
                title="拖动或使用方向键调整共创助手宽度；Home 到最窄，End 到最宽"
                onKeyDown={chatResize.handleKeyDown}
                onPointerDown={chatResize.handlePointerDown}
              >
                <div className={`studio-resizer__handle ${chatResize.dragWidth !== null ? "studio-resizer__handle--dragging" : ""}`}>
                  <div className="studio-resizer__line" />
                </div>
              </div>
            ) : null}
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
              onCopyMarkdown={(markdown) => { void copyMarkdownToClipboard(markdown); }}
              onAppendToDocument={documentModel.appendMarkdownToDocument}
              onAttachFiles={chatModel.handleAttachFiles}
              onComposerTextChange={chatModel.setComposerText}
              onCreateNewDocument={treeActions.handleCreateNewDocument}
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
      </div>

      <UnsavedChangesDialog
        isOpen={navigationGuard.isConfirmOpen}
        isPending={false}
        onClose={navigationGuard.handleDialogClose}
        onConfirm={navigationGuard.handleDialogConfirm}
      />
      <StudioDocumentTreeDialog
        confirmLoading={treeActions.dialogPending}
        description={treeActions.dialogCopy?.description ?? ""}
        nameValue={treeActions.documentTreeDialogValue}
        okText={treeActions.dialogCopy?.okText ?? "确定"}
        open={treeActions.documentTreeDialog !== null}
        title={treeActions.dialogCopy?.title ?? "管理文稿"}
        onCancel={treeActions.closeDocumentTreeDialog}
        onConfirm={treeActions.handleConfirmDocumentTreeDialog}
        onNameChange={treeActions.dialogCopy?.requiresName ? treeActions.setDocumentTreeDialogValue : undefined}
      />
    </>
  );
}
