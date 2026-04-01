"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

type MarkdownDocumentEditorProps = {
  documentPath: string | null;
  documentNode: DocumentTreeNode | null;
  content: string;
  onChange: (content: string) => void;
  onSave: () => void;
  isSaving?: boolean;
  hasUnsavedChanges?: boolean;
};

export function MarkdownDocumentEditor({
  documentPath,
  documentNode,
  content,
  onChange,
  onSave,
  isSaving = false,
  hasUnsavedChanges = false,
}: Readonly<MarkdownDocumentEditorProps>) {
  const [viewMode, setViewMode] = useState<"edit" | "preview" | "split">("edit");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "s") {
      event.preventDefault();
      if (!isSaving && hasUnsavedChanges) {
        onSave();
      }
    }
  }, [isSaving, hasUnsavedChanges, onSave]);

  if (!documentPath) {
    return (
      <div className="flex items-center justify-center h-full bg-[#fefdfb]">
        <div className="text-center max-w-sm px-6">
          <div className="flex items-center justify-center w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-[rgba(107,143,113,0.12)] to-[rgba(196,167,108,0.08)] text-[var(--accent-primary)]">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h3 className="m-0 mb-2 font-serif text-xl font-bold text-[var(--text-primary)]">从左侧挑一份文稿</h3>
          <p className="m-0 text-sm text-[var(--text-muted)] leading-relaxed">设定、大纲、正文和附录都收在同一张写作纸面里，先选中文稿再开始进入正文。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-full min-h-0 bg-[#fefdfb]">
      <div className="absolute inset-0 opacity-[0.015] pointer-events-none [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%221.5%22_numOctaves%3D%224%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />
      
      <header className="relative z-10 flex items-center justify-between gap-4 px-6 py-4 bg-gradient-to-b from-white/95 to-[rgba(254,253,251,0.7)] border-b border-[rgba(44,36,22,0.05)]">
        <div className="absolute bottom-0 left-6 right-6 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)] to-transparent opacity-15" />
        <div className="flex flex-col gap-0.5 min-w-0">
          <p className="m-0 text-[0.68rem] font-semibold tracking-widest uppercase text-[var(--text-muted)]">{documentPath}</p>
          <h2 className="m-0 font-serif text-lg font-bold tracking-tight text-[var(--text-primary)]">{documentNode?.label ?? "未命名文档"}</h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-[rgba(44,36,22,0.04)] rounded-md p-0.5">
            {(["edit", "split", "preview"] as const).map((mode) => (
              <button
                key={mode}
                className={`inline-flex h-[26px] items-center justify-center px-2.5 border-none rounded-[5px] text-[0.72rem] font-semibold cursor-pointer transition-all ${viewMode === mode ? "bg-white text-[var(--text-primary)] shadow-[0_1px_3px_rgba(44,36,22,0.08)]" : "bg-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]"}`}
                onClick={() => setViewMode(mode)}
                type="button"
              >
                {mode === "edit" ? "编辑" : mode === "split" ? "分栏" : "预览"}
              </button>
            ))}
          </div>
          <Button
            type="secondary"
            shape="round"
            size="small"
            loading={isSaving}
            disabled={!hasUnsavedChanges}
            onClick={onSave}
          >
            {isSaving ? "保存中…" : hasUnsavedChanges ? "提醒保存" : "未改动"}
          </Button>
        </div>
      </header>
      
      <div className={`relative z-10 flex flex-1 min-h-0 overflow-hidden ${viewMode === "split" ? "[&>*]:w-1/2" : ""}`} data-mode={viewMode}>
        {viewMode !== "preview" ? (
          <div className="flex flex-col flex-1 min-w-0 bg-transparent">
            <textarea
              ref={textareaRef}
              className="flex-1 w-full max-w-[800px] mx-auto min-h-0 px-6 pt-10 pb-14 border-none bg-transparent text-[var(--text-primary)] font-serif text-base leading-8 tracking-wide resize-none outline-none placeholder:text-[#a09080] placeholder:italic"
              value={content}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="开始整理你的设定、章节或正文…"
              spellCheck={false}
            />
          </div>
        ) : null}
        {viewMode !== "edit" ? (
          <div className="flex flex-col flex-1 min-w-0 overflow-y-auto bg-gradient-to-r from-[rgba(44,36,22,0.02)] to-transparent [background-size:1px_100%]">
            <MarkdownPreview content={content} />
          </div>
        ) : null}
      </div>
      
      <footer aria-live="polite" className="flex items-center justify-between gap-3 px-6 py-2.5 bg-gradient-to-b from-[rgba(254,253,251,0.5)] to-white/80 border-t border-[rgba(44,36,22,0.05)]">
        <span className="text-xs text-[var(--text-muted)]">{content.length} 字符 · {content.split(/\s+/).filter(Boolean).length} 词</span>
        <span className={`text-xs ${hasUnsavedChanges ? "text-[var(--accent-warning)]" : "text-[var(--text-muted)]"}`}>
          {hasUnsavedChanges ? "本地未保存" : "已就绪"}
        </span>
      </footer>
    </div>
  );
}

function MarkdownPreview({ content }: { content: string }) {
  const renderMarkdown = (text: string): string => {
    let html = text
      .replace(/^### (.*$)/gim, "<h3>$1</h3>")
      .replace(/^## (.*$)/gim, "<h2>$1</h2>")
      .replace(/^# (.*$)/gim, "<h1>$1</h1>")
      .replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>")
      .replace(/\*\*(.*)\*\*/gim, "<strong>$1</strong>")
      .replace(/\*(.*)\*/gim, "<em>$1</em>")
      .replace(/`([^`]+)`/gim, "<code>$1</code>")
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/gim, '<img alt="$1" src="$2" />')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/^\- (.*$)/gim, "<li>$1</li>")
      .replace(/^\d+\. (.*$)/gim, "<li>$1</li>")
      .replace(/\n/gim, "<br>");

    html = html.replace(/```(\w*)\n([\s\S]*?)```/gim, (_, lang, code) => {
      return `<pre class="my-3 px-4 py-3 rounded-lg bg-[rgba(44,36,22,0.03)] text-[var(--text-primary)] font-mono text-[0.82rem] leading-relaxed overflow-x-auto border border-[rgba(44,36,22,0.05)]" data-lang="${lang}"><code>${code.trim()}</code></pre>`;
    });

    return html;
  };

  return (
    <div
      className="w-full max-w-[800px] mx-auto px-6 pt-10 pb-14 text-[var(--text-primary)] font-serif text-base leading-8 tracking-wide [&_h1]:my-6 [&_h1]:mb-3 [&_h1]:text-[1.7rem] [&_h1]:font-bold [&_h1]:tracking-tight [&_h1]:leading-tight [&_h1:first-child]:mt-0 [&_h2]:my-5 [&_h2]:mb-2.5 [&_h2]:text-[1.35rem] [&_h2]:font-bold [&_h2]:leading-relaxed [&_h3]:my-4 [&_h3]:mb-2 [&_h3]:text-[1.1rem] [&_h3]:font-semibold [&_h3]:leading-relaxed [&_p]:my-3 [&_blockquote]:my-3.5 [&_blockquote]:py-0.5 [&_blockquote]:pl-3.5 [&_blockquote]:border-l-2 [&_blockquote]:border-[var(--accent-primary)] [&_blockquote]:text-[var(--text-secondary)] [&_blockquote]:italic [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:bg-[rgba(44,36,22,0.06)] [&_code]:text-[#8b4335] [&_code]:font-mono [&_code]:text-[0.88em] [&_a]:text-[var(--accent-primary)] [&_a]:underline [&_a]:underline-offset-2 [&_ul]:my-3 [&_ol]:my-3 [&_ul]:pl-5 [&_ol]:pl-5 [&_li]:my-1 [&_li]:pl-1"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}
