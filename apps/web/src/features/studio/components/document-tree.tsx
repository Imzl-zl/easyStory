"use client";

import { useState } from "react";
import { Button, Dropdown, Menu } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";
import styles from "./document-tree.module.css";

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
    <nav aria-label="作品目录" className={styles.tree}>
      <div className={styles.treeHeader}>
        <div className={styles.treeHeading}>
          <h2 className={styles.treeTitle}>创作结构</h2>
          <p className={styles.treeHint}>设定 · 大纲 · 正文</p>
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
      <ul className={styles.treeList}>
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
    <li className={styles.treeItem}>
      <Dropdown
        trigger="contextMenu"
        droplist={contextMenu}
        position="bl"
      >
        <button
          type="button"
          className={`${styles.treeNode} ${isSelected ? styles.treeNodeSelected : ""}`}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
          onClick={handleClick}
          aria-expanded={isFolder ? expanded : undefined}
        >
          {isFolder ? (
            <span className={`${styles.treeIcon} ${expanded ? styles.treeIconExpanded : ""}`}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </span>
          ) : (
            <span className={styles.treeFileIcon}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </span>
          )}
          <span className={styles.treeLabel}>{node.label}</span>
          {node.icon === "stale" ? (
            <span className={styles.staleIndicator} title="需要更新">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="12" r="4" />
              </svg>
            </span>
          ) : null}
        </button>
      </Dropdown>
      {isFolder && expanded && hasChildren ? (
        <ul className={styles.treeList}>
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
