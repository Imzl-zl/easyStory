"use client";

import { useCallback, useMemo, useState } from "react";
import type { CSSProperties, RefObject } from "react";
import { Checkbox } from "@arco-design/web-react";

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
      <div className="px-3 py-2 border-b border-line-soft">
        <input
          type="text"
          className="chat-panel-search"
          placeholder="搜索文稿..."
          value={contextSearchQuery}
          onChange={(event) => setContextSearchQuery(event.target.value)}
        />
      </div>
      <div className="max-h-52 overflow-y-auto scrollbar-thin py-1">
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
          <p className="chat-panel-empty">没有找到匹配的文稿。</p>
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
    paddingLeft: `${12 + depth * 14}px`,
  } satisfies CSSProperties;

  if (node.type === "file") {
    return (
      <label
        className="flex cursor-pointer items-center gap-2 py-1 pr-3 hover:bg-accent-soft transition-colors"
        style={rowPaddingStyle}
      >
        <Checkbox
          checked={selectedContextPaths.includes(node.path)}
          onChange={() => onToggleContext(node.path)}
        />
        <span className="min-w-0 flex-1 truncate text-sm text-text-primary">
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
        className={`flex w-full items-center gap-2 py-1.5 pr-3 text-left text-xs font-medium text-text-secondary hover:bg-accent-soft transition-colors ${isExpanded ? "bg-accent-soft" : ""}`}
        style={rowPaddingStyle}
        type="button"
        onClick={() => onToggleFolder(node.path, isExpanded)}
      >
        <span className={`transition-transform ${isExpanded ? "rotate-90" : ""}`}>▶</span>
        <span className="min-w-0 flex-1 truncate">{node.label}</span>
        <span className="opacity-60">{visibleFileCount}</span>
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
