"use client";

import { useState } from "react";
import { Button, Dropdown, Menu } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

type DocumentTreeProps = {
  selectedPath: string | null;
  tree: DocumentTreeNode[];
  onSelectNode: (node: DocumentTreeNode) => void;
  onAddNode?: (parentPath: string) => void;
  onRenameNode?: (node: DocumentTreeNode) => void;
  onDeleteNode?: (node: DocumentTreeNode) => void;
};

export function DocumentTree({
  selectedPath,
  tree,
  onSelectNode,
  onAddNode,
  onRenameNode,
  onDeleteNode,
}: Readonly<DocumentTreeProps>) {
  return (
    <nav aria-label="作品目录" className="relative flex flex-col h-full overflow-hidden bg-gradient-to-b from-[#fefdfb] to-[#f9f7f3]">
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%221.2%22_numOctaves%3D%223%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />
      <div className="absolute top-0 left-0 right-0 h-[150px] bg-gradient-to-b from-white/50 to-transparent pointer-events-none" />
      
      <div className="relative z-10 px-5 pt-7 pb-5">
        <div className="flex flex-col gap-1.5">
          <h2 className="m-0 font-serif text-xl font-bold tracking-tight text-[var(--text-primary)]">创作结构</h2>
          <p className="m-0 text-xs text-[var(--text-muted)] leading-relaxed">设定 · 大纲 · 正文</p>
        </div>
        {onAddNode ? (
          <Button
            size="mini"
            shape="circle"
            type="secondary"
            onClick={() => onAddNode("")}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </Button>
        ) : null}
      </div>
      
      <ul className="relative z-10 flex-1 min-h-0 overflow-y-auto px-3 pb-5 scrollbar-thin [&::-webkit-scrollbar]:w-[4px] [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-[2px] [&::-webkit-scrollbar-thumb]:bg-[rgba(44,36,22,0.12)]">
        {tree.map((node) => (
          <DocumentTreeNodeItem
            key={node.id}
            node={node}
            selectedPath={selectedPath}
            onSelectNode={onSelectNode}
            onAddNode={onAddNode}
            onRenameNode={onRenameNode}
            onDeleteNode={onDeleteNode}
            depth={0}
          />
        ))}
      </ul>
    </nav>
  );
}

type DocumentTreeNodeItemProps = {
  node: DocumentTreeNode;
  selectedPath: string | null;
  onSelectNode: (node: DocumentTreeNode) => void;
  onAddNode?: (parentPath: string) => void;
  onRenameNode?: (node: DocumentTreeNode) => void;
  onDeleteNode?: (node: DocumentTreeNode) => void;
  depth: number;
};

function DocumentTreeNodeItem({
  node,
  selectedPath,
  onSelectNode,
  onAddNode,
  onRenameNode,
  onDeleteNode,
  depth,
}: Readonly<DocumentTreeNodeItemProps>) {
  const [expanded, setExpanded] = useState(depth < 1);
  const isFolder = node.type === "folder";
  const isSelected = selectedPath === node.path;
  const hasChildren = node.children && node.children.length > 0;

  const handleClick = () => {
    if (isFolder) {
      setExpanded(!expanded);
    } else {
      onSelectNode(node);
    }
  };

  const contextMenu = onAddNode || onRenameNode || onDeleteNode ? (
    <Menu>
      {isFolder && onAddNode ? (
        <Menu.Item key="add" onClick={() => onAddNode(node.path)}>
          新建文档
        </Menu.Item>
      ) : null}
      {onRenameNode ? (
        <Menu.Item key="rename" onClick={() => onRenameNode(node)}>
          重命名
        </Menu.Item>
      ) : null}
      {onDeleteNode ? (
        <Menu.Item key="delete" onClick={() => onDeleteNode(node)}>
          删除
        </Menu.Item>
      ) : null}
    </Menu>
  ) : null;

  return (
    <li className="mb-0.5">
      <Dropdown
        trigger="contextMenu"
        droplist={contextMenu}
        position="bl"
      >
        <button
          type="button"
          className={`flex items-center gap-2 w-full py-2 px-2.5 border-none rounded-lg bg-transparent text-[var(--text-primary)] text-sm font-medium text-left cursor-pointer transition-all ${isSelected ? "bg-gradient-to-br from-[rgba(107,143,113,0.12)] to-[rgba(107,143,113,0.06)] shadow-[inset_0_0_0_1px_rgba(107,143,113,0.15)] hover:bg-gradient-to-br hover:from-[rgba(107,143,113,0.18)] hover:to-[rgba(107,143,113,0.1)]" : "hover:bg-[rgba(107,143,113,0.08)] hover:translate-x-[3px]"}`}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
          onClick={handleClick}
          aria-expanded={isFolder ? expanded : undefined}
        >
          {isFolder ? (
            <span className={`flex items-center justify-center w-[18px] h-[18px] text-[var(--accent-primary)] text-[0.7rem] transition-transform ${expanded ? "rotate-90" : ""}`}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </span>
          ) : (
            <span className="flex items-center justify-center w-[18px] h-[18px] text-[#c4a76c] text-[0.85rem]">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </span>
          )}
          <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap tracking-tight">{node.label}</span>
          {node.icon === "stale" ? (
            <span className="inline-flex items-center justify-center w-2 h-2 ml-auto rounded-full bg-[#c4a76c] shadow-[0_0_0_2px_rgba(196,167,108,0.2)] animate-[stalePulse_2.5s_ease-in-out_infinite]" title="需要更新">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="12" r="4" />
              </svg>
            </span>
          ) : null}
        </button>
      </Dropdown>
      {isFolder && expanded && hasChildren ? (
        <ul className="overflow-y-auto px-3 pb-5 scrollbar-thin">
          {node.children!.map((child) => (
            <DocumentTreeNodeItem
              key={child.id}
              node={child}
              selectedPath={selectedPath}
              onSelectNode={onSelectNode}
              onAddNode={onAddNode}
              onRenameNode={onRenameNode}
              onDeleteNode={onDeleteNode}
              depth={depth + 1}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
