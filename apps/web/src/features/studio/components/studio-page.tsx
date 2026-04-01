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
    <div className="grid [grid-template-columns:260px_1fr_380px] [grid-template-rows:auto_1fr] h-screen bg-[#fefdfb] relative overflow-hidden">
      <div className="fixed inset-0 opacity-[0.025] pointer-events-none [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%220.9%22_numOctaves%3D%224%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />
      <div className="fixed -top-1/2 -right-[20%] w-full h-[150%] pointer-events-none [background:radial-gradient(ellipse_at_60%_40%,rgba(107,143,113,0.15)_0%,transparent_50%),radial-gradient(ellipse_at_30%_70%,rgba(196,167,108,0.12)_0%,transparent_40%)]" />

      <div className="col-span-3 flex justify-between items-center px-8 py-5 bg-gradient-to-b from-white/98 to-white/85 backdrop-blur-xl border-b border-[rgba(44,36,22,0.06)] relative z-10 animate-[inkFadeIn_0.4s_cubic-bezier(0.16,1,0.3,1)]">
        <div className="absolute bottom-[-1px] left-0 right-0 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)] to-transparent opacity-30" />
        <div className="flex flex-col gap-0.5">
          <p className="m-0 text-[0.65rem] font-semibold tracking-[0.15em] uppercase text-[var(--accent-primary)] opacity-80">当前创作</p>
          <h1 className="m-0 font-serif text-2xl font-bold tracking-tight text-[var(--text-primary)]">{headerTitle}</h1>
          <p className="m-0 text-xs text-[var(--text-secondary)] opacity-70">{projectName} · 正文优先，目录与助手都只是辅助桌面，不抢主舞台。</p>
        </div>
        <div className="flex items-center gap-3">
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
            <span className="relative inline-flex items-center h-[26px] px-3 rounded bg-gradient-to-br from-[var(--accent-primary)] to-[#5a7a60] text-white text-[0.68rem] font-semibold tracking-widest uppercase shadow-[0_2px_8px_rgba(107,143,113,0.25),inset_0_1px_0_rgba(255,255,255,0.15)] overflow-hidden">
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-[inkShimmer_4s_ease-in-out_infinite]" />
              {staleChapters.length} 个章节待整理
            </span>
          ) : null}
        </div>
      </div>

      <div className="contents">
        <aside className="relative z-5 flex flex-col bg-gradient-to-b from-[rgba(254,253,251,0.95)] to-[rgba(249,247,243,0.9)] border-r border-[rgba(44,36,22,0.08)] shadow-[2px_0_20px_rgba(44,36,22,0.03),inset_-1px_0_0_rgba(255,255,255,0.5)] animate-[slideFromLeft_0.5s_cubic-bezier(0.16,1,0.3,1)]">
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

        <main className="relative z-1 flex flex-col bg-[#fefdfb] shadow-[0_0_80px_rgba(44,36,22,0.04),inset_0_0_100px_rgba(255,255,255,0.5)] animate-[inkFadeIn_0.6s_cubic-bezier(0.16,1,0.3,1)]">
          <div className="absolute inset-0 border-x border-[rgba(44,36,22,0.04)] pointer-events-none" />
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
          <aside className="relative z-5 flex flex-col bg-gradient-to-b from-[rgba(254,253,251,0.98)] to-[rgba(249,247,243,0.95)] border-l border-[rgba(44,36,22,0.08)] shadow-[-2px_0_20px_rgba(44,36,22,0.03),inset_1px_0_0_rgba(255,255,255,0.5)] animate-[slideFromRight_0.5s_cubic-bezier(0.16,1,0.3,1)]">
            <div className="absolute top-0 left-0 w-0.5 h-full bg-gradient-to-b from-transparent via-[#c4a76c] to-transparent opacity-25" />
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
