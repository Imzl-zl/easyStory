import type { ChapterSummary } from "@/lib/api/types";

import type { DocumentTreeNode } from "./studio-document-tree";
import {
  findNodeByPath,
  isContentDocumentParentPath,
  isDataLayerDocumentParentPath,
  hasSupportedStudioDocumentSuffix,
  listDocumentTreeFilePaths,
} from "./studio-document-tree";

export type StudioPanelKey = "overview" | "outline" | "opening-plan" | "chapter";
export type StudioChapterListState = "loading" | "error" | "empty" | "ready";
export type StudioDocumentEntryKind = "file" | "folder";

const STUDIO_PANEL_OPTIONS: Array<{
  key: StudioPanelKey;
  label: string;
}> = [
  { key: "overview", label: "项目说明" },
  { key: "outline", label: "大纲" },
  { key: "opening-plan", label: "开篇设计" },
  { key: "chapter", label: "章节" },
];

const PANEL_DEFAULT_DOCUMENT_PATHS: Record<
  Exclude<StudioPanelKey, "chapter">,
  string
> = {
  overview: "项目说明.md",
  outline: "大纲/总大纲.md",
  "opening-plan": "大纲/开篇设计.md",
};

export function buildStudioPathWithParams(
  pathname: string,
  currentSearch: string,
  patches: Record<string, string | null>,
): string {
  const next = new URLSearchParams(currentSearch);
  Object.entries(patches).forEach(([key, value]) => {
    if (value === null) {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  const search = next.toString();
  return search ? `${pathname}?${search}` : pathname;
}

export function listStudioPanelOptions() {
  return STUDIO_PANEL_OPTIONS;
}

export function getStudioPanelLabel(panel: StudioPanelKey) {
  return STUDIO_PANEL_OPTIONS.find((item) => item.key === panel)?.label ?? "项目说明";
}

export function resolveStudioChapterListState({
  chapters,
  errorMessage,
  isLoading,
}: {
  chapters: ChapterSummary[] | undefined;
  errorMessage: string | null;
  isLoading: boolean;
}): StudioChapterListState {
  if (isLoading && !chapters) {
    return "loading";
  }
  if (errorMessage && (!chapters || chapters.length === 0)) {
    return "error";
  }
  if (!chapters || chapters.length === 0) {
    return "empty";
  }
  return "ready";
}

export function resolveSelectedChapterNumber(
  chapters: ChapterSummary[] | undefined,
  rawChapter: string | null,
) {
  if (rawChapter) {
    const parsed = Number(rawChapter);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  const firstStale = chapters?.find((chapter) => chapter.status === "stale");
  return firstStale?.chapter_number ?? chapters?.[0]?.chapter_number ?? null;
}

export function listStaleChapters(chapters: ChapterSummary[] | undefined) {
  return chapters?.filter((chapter) => chapter.status === "stale") ?? [];
}

export function resolveStudioPanel(value: string | null): StudioPanelKey {
  return STUDIO_PANEL_OPTIONS.some((item) => item.key === value)
    ? (value as StudioPanelKey)
    : "overview";
}

export function resolveDefaultDocumentPathFromPanel(
  panelValue: string | null,
  chapters: ChapterSummary[] | undefined,
  rawChapter: string | null,
) {
  const panel = STUDIO_PANEL_OPTIONS.find((item) => item.key === panelValue)?.key;
  if (!panel) {
    return null;
  }
  if (panel === "chapter") {
    const chapterNumber = resolveSelectedChapterNumber(chapters, rawChapter);
    return chapterNumber === null
      ? null
      : `正文/第${String(chapterNumber).padStart(3, "0")}章.md`;
  }
  return PANEL_DEFAULT_DOCUMENT_PATHS[panel];
}

export function resolveDocumentPathFromNode(node: DocumentTreeNode): string {
  return node.path;
}

export function resolveStudioDocumentPath(
  rawDocumentPath: string | null,
  tree: DocumentTreeNode[],
  treeReady: boolean,
  fallbackDocumentPath: string | null,
) {
  if (!rawDocumentPath) {
    return fallbackDocumentPath;
  }
  if (!treeReady) {
    return null;
  }
  return findNodeByPath(tree, rawDocumentPath)?.path ?? fallbackDocumentPath;
}

export function findClosestRemainingFilePath(
  tree: DocumentTreeNode[],
  removedPath: string,
  currentPath: string | null,
) {
  const filePaths = listDocumentTreeFilePaths(tree);
  const remainingPaths = filePaths.filter((path) => !isDocumentTreePathAffected(path, removedPath));
  if (remainingPaths.length === 0) {
    return null;
  }
  if (!currentPath) {
    return remainingPaths[0] ?? null;
  }
  const currentIndex = filePaths.findIndex((path) => path === currentPath);
  if (currentIndex === -1) {
    return remainingPaths[0] ?? null;
  }
  for (let index = currentIndex + 1; index < filePaths.length; index += 1) {
    const candidatePath = filePaths[index];
    if (candidatePath && !isDocumentTreePathAffected(candidatePath, removedPath)) {
      return candidatePath;
    }
  }
  for (let index = currentIndex - 1; index >= 0; index -= 1) {
    const candidatePath = filePaths[index];
    if (candidatePath && !isDocumentTreePathAffected(candidatePath, removedPath)) {
      return candidatePath;
    }
  }
  return remainingPaths[0] ?? null;
}

export function isDocumentTreePathAffected(path: string, targetPath: string) {
  return path === targetPath || path.startsWith(`${targetPath}/`);
}

export function remapDocumentTreePath(
  path: string,
  previousPath: string,
  nextPath: string | null,
): string | null {
  if (!isDocumentTreePathAffected(path, previousPath)) {
    return path;
  }
  if (nextPath === null) {
    return null;
  }
  if (path === previousPath) {
    return nextPath;
  }
  return `${nextPath}${path.slice(previousPath.length)}`;
}

export function buildStudioDocumentEntryPath(
  parentPath: string,
  rawName: string,
  kind: StudioDocumentEntryKind,
): string | null {
  const normalizedName = normalizeStudioDocumentEntryName(parentPath, rawName, kind);
  if (!normalizedName) {
    return null;
  }
  return parentPath ? `${parentPath}/${normalizedName}` : normalizedName;
}

export function normalizeStudioDocumentEntryName(
  parentPath: string,
  rawName: string,
  kind: StudioDocumentEntryKind,
): string | null {
  const trimmed = rawName.trim();
  if (!trimmed || trimmed === "." || trimmed === "..") {
    return null;
  }
  if (trimmed.includes("/") || trimmed.includes("\\")) {
    return null;
  }
  if (kind === "file" && isContentDocumentParentPath(parentPath)) {
    return normalizeStudioChapterEntryName(trimmed);
  }
  if (kind === "folder") {
    return hasSupportedStudioDocumentSuffix(trimmed) ? null : trimmed;
  }
  if (isDataLayerDocumentParentPath(parentPath)) {
    return hasSupportedStudioDocumentSuffix(trimmed) ? trimmed : `${trimmed}.json`;
  }
  return hasSupportedStudioDocumentSuffix(trimmed) ? trimmed : `${trimmed}.md`;
}

export function readStudioDocumentEntryBaseName(node: DocumentTreeNode) {
  const leafName = node.path.split("/").at(-1) ?? "";
  return node.type === "file" ? leafName.replace(/\.(json|md)$/i, "") : leafName;
}

function normalizeStudioChapterEntryName(rawName: string) {
  const chapterName = rawName.replace(/\.md$/i, "");
  const matched = chapterName.match(/^(?:第)?\s*(\d{1,3})\s*章?$/);
  if (!matched) {
    return null;
  }
  const chapterNumber = Number(matched[1]);
  if (!Number.isInteger(chapterNumber) || chapterNumber <= 0) {
    return null;
  }
  return `第${String(chapterNumber).padStart(3, "0")}章.md`;
}

export type DocumentTreeDialogState =
  | { mode: "create-file"; parentLabel: string; parentPath: string }
  | { mode: "create-folder"; parentLabel: string; parentPath: string }
  | { mode: "delete"; node: DocumentTreeNode }
  | { mode: "rename"; node: DocumentTreeNode }
  | null;

export function buildDocumentTreeDialogCopy(dialog: DocumentTreeDialogState): {
  description: string;
  okText: string;
  requiresName: boolean;
  title: string;
} | null {
  if (!dialog) {
    return null;
  }
  if (dialog.mode === "create-file") {
    return {
      description: readCreateDocumentDescription(dialog.parentPath),
      okText: isContentDocumentParentPath(dialog.parentPath) ? "新建章节" : "新建文稿",
      requiresName: true,
      title: isContentDocumentParentPath(dialog.parentPath) ? "新建章节" : "新建文稿",
    };
  }
  if (dialog.mode === "create-folder") {
    return {
      description: isContentDocumentParentPath(dialog.parentPath)
        ? `在"${dialog.parentLabel}"下新建卷目录或正文分组。`
        : `在"${dialog.parentLabel}"下新建一个自定义目录。`,
      okText: "新建目录",
      requiresName: true,
      title: "新建目录",
    };
  }
  if (dialog.mode === "rename") {
    return {
      description: `修改"${dialog.node.label}"的名称。`,
      okText: "确认重命名",
      requiresName: true,
      title: dialog.node.type === "file" ? "重命名文稿" : "重命名目录",
    };
  }
  return dialog.mode === "delete"
    ? {
      description: dialog.node.type === "file"
        ? `删除"${dialog.node.label}"后，这份自定义文稿将从项目文稿树中移除。`
        : `删除"${dialog.node.label}"后，这个目录和其中的自定义文稿都会一起移除。`,
      okText: "确认删除",
      requiresName: false,
      title: dialog.node.type === "file" ? "删除文稿" : "删除目录",
    }
    : null;
}

export function readDocumentTreeParentPath(path: string) {
  return path.split("/").slice(0, -1).join("/");
}

export function readDocumentTreeLabel(path: string) {
  if (!path) {
    return "根目录";
  }
  return path.split("/").at(-1) ?? path;
}

export function readInvalidDocumentEntryNameMessage(kind: "file" | "folder", parentPath = "") {
  if (kind === "file") {
    if (isContentDocumentParentPath(parentPath)) {
      return "章节号不能为空，且只能输入类似 1、001 或 第1章。";
    }
    return "文稿名不能为空，不能包含斜杠；默认创建 .md，输入 .json 会保留为 JSON 文件。";
  }
  return "目录名不能为空，不能包含斜杠，也不能以 .md 或 .json 结尾。";
}

function readCreateDocumentDescription(parentPath: string) {
  if (isContentDocumentParentPath(parentPath)) {
    return `在"${readDocumentTreeLabel(parentPath)}"下新建章节文稿，输入章节号即可，例如 1 或第1章。`;
  }
  return `在"${readDocumentTreeLabel(parentPath)}"下新建一份文稿文件；默认是 .md，输入 .json 会直接创建 JSON。`;
}

export async function copyMarkdownToClipboard(markdown: string) {
  const { default: ArcoMessage } = await import("@arco-design/web-react/es/Message");
  try {
    await navigator.clipboard.writeText(markdown);
    ArcoMessage.success("已复制到剪贴板");
  } catch {
    ArcoMessage.error("复制失败，请检查浏览器剪贴板权限后重试。");
  }
}
