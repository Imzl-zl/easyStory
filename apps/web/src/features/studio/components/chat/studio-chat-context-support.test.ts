import assert from "node:assert/strict";
import test from "node:test";

import type { DocumentTreeNode } from "@/features/studio/components/page/studio-page-support";

import {
  buildStudioContextFileCountMap,
  countStudioContextFiles,
  countStudioContextFilesForNode,
  filterStudioContextTree,
} from "@/features/studio/components/chat/studio-chat-context-support";

test("countStudioContextFiles counts nested files under the same tree used by Studio", () => {
  const tree = buildContextTreeFixture();

  assert.equal(countStudioContextFiles(tree), 6);
  assert.equal(countStudioContextFilesForNode(tree[1] as DocumentTreeNode), 2);
  assert.equal(countStudioContextFilesForNode(tree[3] as DocumentTreeNode), 2);
});

test("buildStudioContextFileCountMap computes descendant file counts in one traversal result", () => {
  const fileCountByPath = buildStudioContextFileCountMap(buildContextTreeFixture());

  assert.equal(fileCountByPath.get("项目说明.md"), 1);
  assert.equal(fileCountByPath.get("设定"), 2);
  assert.equal(fileCountByPath.get("数据层"), 1);
  assert.equal(fileCountByPath.get("正文/第一卷"), 2);
  assert.equal(fileCountByPath.get("正文"), 2);
});

test("filterStudioContextTree keeps matching ancestors instead of regrouping by keywords", () => {
  const filteredTree = filterStudioContextTree(buildContextTreeFixture(), "人物");

  assert.deepEqual(collectContextPaths(filteredTree), [
    "设定",
    "设定/人物.md",
    "数据层",
    "数据层/人物.json",
  ]);
});

test("filterStudioContextTree returns the full subtree when the folder itself matches", () => {
  const filteredTree = filterStudioContextTree(buildContextTreeFixture(), "正文");

  assert.deepEqual(collectContextPaths(filteredTree), [
    "正文",
    "正文/第一卷",
    "正文/第一卷/第001章.md",
    "正文/第一卷/第002章.md",
  ]);
});

function buildContextTreeFixture(): DocumentTreeNode[] {
  return [
    {
      id: "doc-intro",
      label: "项目说明.md",
      origin: "custom",
      path: "项目说明.md",
      type: "file",
    },
    {
      children: [
        {
          id: "doc-cast",
          label: "人物.md",
          origin: "custom",
          path: "设定/人物.md",
          type: "file",
        },
        {
          id: "doc-world",
          label: "世界观.md",
          origin: "custom",
          path: "设定/世界观.md",
          type: "file",
        },
      ],
      id: "folder-setting",
      label: "设定",
      origin: "fixed",
      path: "设定",
      type: "folder",
    },
    {
      children: [
        {
          id: "doc-character-data",
          label: "人物.json",
          origin: "custom",
          path: "数据层/人物.json",
          type: "file",
        },
      ],
      id: "folder-data",
      label: "数据层",
      origin: "custom",
      path: "数据层",
      type: "folder",
    },
    {
      children: [
        {
          children: [
            {
              id: "doc-ch1",
              label: "第001章.md",
              origin: "database",
              path: "正文/第一卷/第001章.md",
              type: "file",
            },
            {
              id: "doc-ch2",
              label: "第002章.md",
              origin: "database",
              path: "正文/第一卷/第002章.md",
              type: "file",
            },
          ],
          id: "folder-volume-1",
          label: "第一卷",
          origin: "custom",
          path: "正文/第一卷",
          type: "folder",
        },
      ],
      id: "folder-content",
      label: "正文",
      origin: "fixed",
      path: "正文",
      type: "folder",
    },
  ];
}

function collectContextPaths(nodes: readonly DocumentTreeNode[]): string[] {
  return nodes.flatMap((node) => [
    node.path,
    ...(node.children ? collectContextPaths(node.children) : []),
  ]);
}
