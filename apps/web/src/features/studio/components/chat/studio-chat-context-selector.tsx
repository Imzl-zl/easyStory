"use client";

import { useCallback, useMemo, useState } from "react";
import type { CSSProperties, RefObject } from "react";

import type { DocumentTreeNode } from "@/features/studio/components/page/studio-page-support";

import {
  buildStudioContextFileCountMap,
  countStudioContextFiles,
  filterStudioContextTree,
} from "@/features/studio/components/chat/studio-chat-context-support";

type StudioChatContextSelectorContentProps = {
  availableContexts: DocumentTreeNode[];
  onToggleContext: (path: string) => void;
  panelRef: RefObject<HTMLDivElement | null>;
  panelStyle: CSSProperties | undefined;
  selectedContextPaths: string[];
};

export function StudioChatContextSelectorContent({
  availableContexts,
  onToggleContext,
  panelRef,
  panelStyle,
  selectedContextPaths,
}: Readonly<StudioChatContextSelectorContentProps>) {
  const [contextSearchQuery, setContextSearchQuery] = useState("");
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({});

  const { filteredContexts, filteredFileCountByPath } = useMemo(() => {
    const nextFilteredContexts = filterStudioContextTree(availableContexts, contextSearchQuery);
    return {
      filteredContexts: nextFilteredContexts,
      filteredFileCountByPath: buildStudioContextFileCountMap(nextFilteredContexts),
    };
  },
    [availableContexts, contextSearchQuery],
  );
  const totalFileCount = useMemo(
    () => countStudioContextFiles(availableContexts),
    [availableContexts],
  );
  const isSearching = contextSearchQuery.trim().length > 0;

  const toggleFolder = useCallback((path: string, isExpanded: boolean) => {
    setExpandedPaths((current) => ({
      ...current,
      [path]: !isExpanded,
    }));
  }, []);

  return (
    <div
      className="chat-context-panel"
      ref={panelRef}
      style={panelStyle}
    >
      <div className="chat-panel-header">
        <div>
          <h3 className="chat-panel-header__title">附加文档上下文</h3>
          <p className="chat-panel-header__subtitle">已选 {selectedContextPaths.length} / {totalFileCount} 个文件</p>
        </div>
      </div>
      <div className="px-5 py-3 border-t border-[rgba(150,158,170,0.08)]">
        <input
          type="text"
          className="chat-panel-search"
          placeholder="搜索文稿..."
          value={contextSearchQuery}
          onChange={(event) => setContextSearchQuery(event.target.value)}
        />
      </div>
      <div className="max-h-64 overflow-y-auto scrollbar-thin py-2">
        {filteredContexts.length > 0 ? (
          filteredContexts.map((node) => (
            <StudioChatContextTreeNode
              depth={0}
              expandedPaths={expandedPaths}
              fileCountByPath={filteredFileCountByPath}
              isSearching={isSearching}
              key={node.id}
              node={node}
              selectedContextPaths={selectedContextPaths}
              onToggleContext={onToggleContext}
              onToggleFolder={toggleFolder}
            />
          ))
        ) : (
          <p className="chat-panel-empty">无匹配结果</p>
        )}
      </div>
    </div>
  );
}

type StudioChatContextTreeNodeProps = {
  depth: number;
  expandedPaths: Record<string, boolean>;
  fileCountByPath: ReadonlyMap<string, number>;
  isSearching: boolean;
  node: DocumentTreeNode;
  onToggleContext: (path: string) => void;
  onToggleFolder: (path: string, isExpanded: boolean) => void;
  selectedContextPaths: string[];
};

function StudioChatContextTreeNode({
  depth,
  expandedPaths,
  fileCountByPath,
  isSearching,
  node,
  onToggleContext,
  onToggleFolder,
  selectedContextPaths,
}: Readonly<StudioChatContextTreeNodeProps>) {
  const rowPaddingStyle = {
    paddingLeft: `${16 + depth * 16}px`,
  } satisfies CSSProperties;

  if (node.type === "file") {
    const checked = selectedContextPaths.includes(node.path);
    return (
      <label
        className="flex cursor-pointer items-center gap-2.5 py-1.5 pr-4 hover:bg-[rgba(150,158,170,0.05)] transition-colors"
        style={rowPaddingStyle}
      >
        <CustomCheckbox checked={checked} onChange={() => onToggleContext(node.path)} />
        <span className="min-w-0 flex-1 truncate text-[14px] text-[#dde1e6]">
          {node.label}
        </span>
      </label>
    );
  }

  const visibleFileCount = fileCountByPath.get(node.path) ?? 0;
  const hasSelectedDescendant = selectedContextPaths.some((path) => path.startsWith(`${node.path}/`));
  const isExpanded = isSearching
    || expandedPaths[node.path]
    || (!(node.path in expandedPaths) && (depth === 0 || hasSelectedDescendant));

  return (
    <div>
      <button
        className={`flex w-full items-center gap-2.5 py-2 pr-4 text-left text-[13px] font-semibold text-[#9299a3] hover:bg-[rgba(150,158,170,0.05)] transition-colors ${isExpanded ? "text-[#dde1e6]" : ""}`}
        style={rowPaddingStyle}
        type="button"
        onClick={() => onToggleFolder(node.path, isExpanded)}
      >
        <span className={`text-[10px] transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`}>▶</span>
        <span className="min-w-0 flex-1 truncate">{node.label}</span>
        <span className="text-[11px] text-[#686e77] bg-[#2f343e] px-2 py-0.5 rounded-full">{visibleFileCount}</span>
      </button>
      {isExpanded
        ? node.children?.map((child) => (
          <StudioChatContextTreeNode
            depth={depth + 1}
            expandedPaths={expandedPaths}
            fileCountByPath={fileCountByPath}
            isSearching={isSearching}
            key={child.id}
            node={child}
            selectedContextPaths={selectedContextPaths}
            onToggleContext={onToggleContext}
            onToggleFolder={onToggleFolder}
          />
        ))
        : null}
    </div>
  );
}

function CustomCheckbox({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <span
      className={`inline-flex items-center justify-center size-[16px] rounded-[4px] border transition-all duration-150 cursor-pointer shrink-0 ${
        checked
          ? "bg-[#a09682] border-[#a09682]"
          : "bg-transparent border-[rgba(150,158,170,0.30)] hover:border-[rgba(160,150,130,0.50)]"
      }`}
      role="checkbox"
      aria-checked={checked}
      onClick={onChange}
    >
      {checked ? (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
          <path d="M5 12l5 5L20 7" stroke="#1a1d24" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ) : null}
    </span>
  );
}
