"use client";

import { useMemo, useTransition, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Button, Message } from "@arco-design/web-react";

import { DocumentTree } from "@/features/studio/components/document-tree";
import { MarkdownDocumentEditor } from "@/features/studio/components/markdown-document-editor";
import { AiChatPanel } from "@/features/studio/components/ai-chat-panel";
import { useStudioChatModel } from "@/features/studio/components/studio-chat-model";
import {
  buildDocumentTreeFromChapters,
  buildStudioPathWithParams,
  findNodeByPath,
  listStaleChapters,
} from "@/features/studio/components/studio-page-support";
import { listChapters } from "@/lib/api/content";
import { getProject } from "@/lib/api/projects";
import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";
import styles from "./studio-page.module.css";

type StudioPageProps = {
  projectId: string;
};

export function StudioPage({ projectId }: StudioPageProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();
  const currentSearch = searchParams.toString();

  const documentPath = searchParams.get("doc");
  const chatOpen = searchParams.get("chat") !== "0";

  const [documentContent, setDocumentContent] = useState("");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

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
  const chatModel = useStudioChatModel({
    currentDocumentContent: documentContent,
    currentDocumentPath: documentPath,
    projectId,
  });

  const updateParams = useCallback((patches: Record<string, string | null>) => {
    startTransition(() => {
      router.replace(buildStudioPathWithParams(pathname, currentSearch, patches));
    });
  }, [currentSearch, pathname, router, startTransition]);

  const handleSelectNode = useCallback((node: DocumentTreeNode) => {
    if (node.type === "file") {
      if (hasUnsavedChanges) {
        const confirmed = window.confirm("当前文档还有未保存内容，切换后会保留在本地编辑区，稍后再接入正式保存。是否继续？");
        if (!confirmed) {
          return;
        }
      }
      updateParams({ doc: node.path });
      setDocumentContent("");
      setHasUnsavedChanges(false);
    }
  }, [hasUnsavedChanges, updateParams]);

  const handleContentChange = useCallback((content: string) => {
    setDocumentContent(content);
    setHasUnsavedChanges(true);
  }, []);

  const handleSave = useCallback(() => {
    Message.info("保存能力正在接入，当前仅保留本地编辑内容。");
  }, []);

  const handleCopyMarkdown = useCallback((markdown: string) => {
    navigator.clipboard.writeText(markdown);
    Message.success("已复制到剪贴板");
  }, []);

  const handleAppendToDocument = useCallback((markdown: string) => {
    setDocumentContent((prev) => (prev ? `${prev}\n\n${markdown}` : markdown));
    setHasUnsavedChanges(true);
    Message.success("已追加到当前文档");
  }, []);

  const handleCreateNewDocument = useCallback(() => {
    Message.info("新建文档写入能力正在接入。");
  }, []);

  const toggleChat = useCallback(() => {
    updateParams({ chat: chatOpen ? "0" : null });
  }, [chatOpen, updateParams]);

  return (
    <div className={styles.page}>
      <div className={styles.pageMeta}>
        <div className={styles.projectInfo}>
          <p className={styles.projectEyebrow}>当前创作</p>
          <h1 className={styles.projectTitle}>{headerTitle}</h1>
          <p className={styles.projectHint}>{projectName} · 正文优先，目录与助手都只是辅助桌面，不抢主舞台。</p>
        </div>
        <div className={styles.pageActions}>
          <Button shape="round" size="small" type="secondary" onClick={toggleChat}>
            {chatOpen ? "收起助手" : "展开助手"}
          </Button>
          <Button
            shape="round"
            size="small"
            type="secondary"
            onClick={() => router.push(`/workspace/project/${projectId}/engine`)}
          >
            作品推进
          </Button>
          {staleChapters.length > 0 ? (
            <span className={styles.statusChip}>{staleChapters.length} 个章节待整理</span>
          ) : null}
        </div>
      </div>

      <div className={styles.mainLayout}>
        <aside className={styles.sidebar}>
          <DocumentTree
            selectedPath={documentPath}
            tree={documentTree}
            onSelectNode={handleSelectNode}
          />
          {staleChapters.length > 0 ? (
            <div className={styles.staleNotice}>
              <p className={styles.staleTitle}>待更新章节</p>
              <p className={styles.staleDescription}>{staleChapters.length} 个章节需要重新整理到当前上下文。</p>
            </div>
          ) : null}
        </aside>

        <main className={styles.content}>
          <MarkdownDocumentEditor
            documentPath={documentPath}
            documentNode={selectedNode}
            content={documentContent}
            onChange={handleContentChange}
            onSave={handleSave}
            hasUnsavedChanges={hasUnsavedChanges}
          />
        </main>

        {chatOpen ? (
          <aside className={styles.chat}>
            <AiChatPanel
              attachments={chatModel.attachments}
              availableContexts={documentTree}
              canChat={chatModel.credentialModel.canChat}
              credentialNotice={chatModel.credentialModel.credentialNotice}
              credentialSettingsHref={chatModel.credentialModel.credentialSettingsHref}
              credentialState={chatModel.credentialModel.credentialState}
              currentDocumentPath={documentPath}
              isCredentialLoading={chatModel.credentialModel.isCredentialLoading}
              isResponding={chatModel.isResponding}
              messages={chatModel.messages}
              onCopyMarkdown={handleCopyMarkdown}
              onAppendToDocument={handleAppendToDocument}
              onAttachFiles={chatModel.handleAttachFiles}
              onCreateNewDocument={handleCreateNewDocument}
              onModelNameChange={chatModel.handleModelNameChange}
              onProviderChange={chatModel.handleProviderChange}
              onRemoveAttachment={chatModel.handleRemoveAttachment}
              onSendMessage={chatModel.handleSendMessage}
              onToggleContext={chatModel.handleToggleContext}
              providerOptions={chatModel.credentialModel.providerOptions}
              selectedContextPaths={chatModel.selectedContextPaths}
              selectedCredentialLabel={chatModel.selectedCredentialLabel}
              settings={chatModel.settings}
              visibleModelLabel={chatModel.visibleModelLabel}
            />
          </aside>
        ) : null}
      </div>
    </div>
  );
}
