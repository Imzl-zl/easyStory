"use client";

import { useMemo, useTransition, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Message } from "@arco-design/web-react";

import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import { DocumentTree } from "@/features/studio/components/document-tree";
import { MarkdownDocumentEditor } from "@/features/studio/components/markdown-document-editor";
import { AiChatPanel } from "@/features/studio/components/ai-chat-panel";
import { useStudioDocumentModel } from "@/features/studio/components/studio-document-model";
import { useStudioChatModel } from "@/features/studio/components/studio-chat-model";
import {
  buildDocumentTreeFromChapters,
  buildStudioPathWithParams,
  findNodeByPath,
  listStaleChapters,
} from "@/features/studio/components/studio-page-support";
import { listChapters } from "@/lib/api/content";
import { getProject } from "@/lib/api/projects";
import { useUnsavedChangesGuard } from "@/lib/hooks/use-unsaved-changes-guard";
import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

type StudioPageProps = {
  projectId: string;
};

const STUDIO_TOOLBAR_BUTTON_CLASS = "ink-button-secondary whitespace-nowrap";
const STUDIO_SAVE_BUTTON_CLASS =
  "ink-button whitespace-nowrap h-9 px-4 text-[13px] shadow-[0_10px_18px_rgba(90,122,107,0.14)]";
const STUDIO_STALE_BADGE_CLASS =
  "inline-flex items-center gap-2 h-8 px-3.5 rounded-full border border-[rgba(90,122,107,0.16)] bg-[rgba(90,122,107,0.08)] text-[0.72rem] font-semibold tracking-[0.16em] uppercase text-[var(--accent-primary)]";
const STUDIO_STALE_BADGE_DOT_CLASS =
  "inline-flex h-1.5 w-1.5 rounded-full bg-[var(--accent-tertiary)] shadow-[0_0_0_4px_rgba(196,167,125,0.12)]";

export function StudioPage({ projectId }: StudioPageProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();
  const currentSearch = searchParams.toString();
  const currentUrl = currentSearch ? `${pathname}?${currentSearch}` : pathname;

  const documentPath = searchParams.get("doc");
  const chatOpen = searchParams.get("chat") !== "0";

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const chaptersQuery = useQuery({
    queryKey: ["chapters", projectId],
    queryFn: () => listChapters(projectId),
  });

  const documentTree = useMemo(() => {
    return buildDocumentTreeFromChapters(chaptersQuery.data ?? []);
  }, [chaptersQuery.data]);

  const selectedNode = useMemo(() => {
    if (!documentPath) {
      return null;
    }
    return findNodeByPath(documentTree, documentPath);
  }, [documentTree, documentPath]);

  const staleChapters = useMemo(() => listStaleChapters(chaptersQuery.data), [chaptersQuery.data]);
  const projectName = projectQuery.data?.name ?? "正在加载项目…";
  const headerTitle = selectedNode?.label ?? "选择一份文稿开始写作";
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
    currentDocumentContent: documentModel.documentContent,
    currentDocumentPath: documentPath,
    projectId,
  });

  const updateParams = useCallback((patches: Record<string, string | null>) => {
    startTransition(() => {
      router.replace(buildStudioPathWithParams(pathname, currentSearch, patches));
    });
  }, [currentSearch, pathname, router, startTransition]);

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

  const handleCreateNewDocument = useCallback(() => {
    Message.info("新建文档写入能力正在接入。");
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

  return (
    <>
      <div className="grid [grid-template-columns:1fr] lg:[grid-template-columns:248px_minmax(0,1fr)_360px] [grid-template-rows:auto_minmax(0,1fr)] h-full min-h-0 bg-[#fefdfb] relative overflow-hidden">
        <div className="fixed -top-1/2 -right-[20%] w-full h-[150%] pointer-events-none [background:radial-gradient(ellipse_at_60%_40%,rgba(107,143,113,0.15)_0%,transparent_50%),radial-gradient(ellipse_at_30%_70%,rgba(196,167,108,0.12)_0%,transparent_40%)]" />

        <div className="col-span-3 flex justify-between items-center gap-4 px-5 py-2.5 bg-gradient-to-b from-white/98 to-white/88 backdrop-blur-xl border-b border-[rgba(44,36,22,0.06)] relative z-10 animate-[inkFadeIn_0.4s_cubic-bezier(0.16,1,0.3,1)]">
          <div className="absolute bottom-[-1px] left-0 right-0 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)] to-transparent opacity-30" />
          <div className="flex min-w-0 flex-col gap-0.5">
            <p className="m-0 truncate text-[0.68rem] font-semibold tracking-[0.14em] uppercase text-[var(--accent-primary)] opacity-80">{projectName}</p>
            <h1 className="m-0 truncate font-serif text-[1.12rem] font-bold tracking-tight text-[var(--text-primary)]">{headerTitle}</h1>
          </div>
          <div className="flex items-center gap-2.5">
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
          <aside className="relative z-5 flex min-h-0 flex-col overflow-hidden bg-gradient-to-b from-[rgba(254,253,251,0.95)] to-[rgba(249,247,243,0.9)] border-r border-[rgba(44,36,22,0.08)] shadow-[2px_0_20px_rgba(44,36,22,0.03),inset_-1px_0_0_rgba(255,255,255,0.5)] animate-[slideFromLeft_0.5s_cubic-bezier(0.16,1,0.3,1)]">
            <div className="absolute top-0 right-0 w-0.5 h-full bg-gradient-to-b from-transparent via-[var(--accent-primary)] to-transparent opacity-20" />
            <DocumentTree
              selectedPath={documentPath}
              tree={documentTree}
              onSelectNode={handleSelectNode}
            />
            {staleChapters.length > 0 ? (
              <div className="relative mx-4 my-4 px-5 py-4 pl-6 rounded-lg bg-gradient-to-br from-[rgba(196,167,108,0.08)] to-[rgba(196,167,108,0.03)] border border-[rgba(196,167,108,0.2)] shadow-[0_4px_16px_rgba(196,167,108,0.1),inset_0_1px_0_rgba(255,255,255,0.3)]">
                <div className="absolute top-0 left-0 w-[3px] h-full bg-gradient-to-b from-[#c4a76c] via-[rgba(196,167,108,0.5)] to-[#c4a76c] rounded-l-lg" />
                <p className="m-0 mb-1 text-sm font-semibold text-[var(--text-primary)]">待更新章节</p>
                <p className="m-0 text-xs text-[var(--text-secondary)] leading-relaxed">{staleChapters.length} 个章节需要重新整理到当前上下文。</p>
              </div>
            ) : null}
          </aside>

          <main className="relative z-1 flex min-h-0 flex-col overflow-hidden bg-[#fefdfb] shadow-[0_0_80px_rgba(44,36,22,0.04),inset_0_0_100px_rgba(255,255,255,0.5)] animate-[inkFadeIn_0.6s_cubic-bezier(0.16,1,0.3,1)]">
            <div className="absolute inset-0 border-x border-[rgba(44,36,22,0.04)] pointer-events-none" />
            <MarkdownDocumentEditor
              documentPath={documentPath}
              documentNode={selectedNode}
              content={documentModel.documentContent}
              isLoading={documentModel.isDocumentLoading}
              isSaving={documentModel.isSaving}
              saveNoun={documentModel.saveNoun}
              onChange={documentModel.handleContentChange}
              onSave={documentModel.handleSave}
              hasUnsavedChanges={documentModel.hasUnsavedChanges}
            />
          </main>

          {chatOpen ? (
            <aside className="relative z-5 flex min-h-0 min-w-0 flex-col overflow-hidden bg-gradient-to-b from-[rgba(254,253,251,0.98)] to-[rgba(249,247,243,0.95)] border-l border-[rgba(44,36,22,0.08)] shadow-[-2px_0_20px_rgba(44,36,22,0.03),inset_1px_0_0_rgba(255,255,255,0.5)] animate-[slideFromRight_0.5s_cubic-bezier(0.16,1,0.3,1)]">
              <div className="absolute top-0 left-0 w-0.5 h-full bg-gradient-to-b from-transparent via-[#c4a76c] to-transparent opacity-25" />
              <AiChatPanel
                activeConversationId={chatModel.activeConversationId}
                attachments={chatModel.attachments}
                availableContexts={documentTree}
                canChat={chatModel.credentialModel.canChat}
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
                onRemoveAttachment={chatModel.handleRemoveAttachment}
                onSendMessage={chatModel.handleSendMessage}
                onStreamOutputChange={chatModel.handleStreamOutputChange}
                onToggleContext={chatModel.handleToggleContext}
                providerOptions={chatModel.credentialModel.providerOptions}
                selectConversation={chatModel.selectConversation}
                selectedContextPaths={chatModel.selectedContextPaths}
                selectedCredentialLabel={chatModel.selectedCredentialLabel}
                settings={chatModel.settings}
                visibleModelLabel={chatModel.visibleModelLabel}
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
    </>
  );
}

async function copyMarkdownToClipboard(markdown: string) {
  try {
    await navigator.clipboard.writeText(markdown);
    Message.success("已复制到剪贴板");
  } catch {
    Message.error("复制失败，请检查浏览器剪贴板权限后重试。");
  }
}
