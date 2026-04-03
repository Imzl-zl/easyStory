import type { ChapterSummary } from "@/lib/api/types";

export type StudioPanelKey = "setting" | "outline" | "opening-plan" | "chapter";
export type StudioChapterListState = "loading" | "error" | "empty" | "ready";

export type DocumentTreeNode = {
  id: string;
  label: string;
  type: "folder" | "file";
  icon?: string;
  children?: DocumentTreeNode[];
  path: string;
};

const STUDIO_PANEL_OPTIONS: Array<{
  key: StudioPanelKey;
  label: string;
}> = [
  { key: "setting", label: "设定" },
  { key: "outline", label: "大纲" },
  { key: "opening-plan", label: "开篇设计" },
  { key: "chapter", label: "章节" },
];

const PANEL_DEFAULT_DOCUMENT_PATHS: Record<
  Exclude<StudioPanelKey, "chapter">,
  string
> = {
  setting: "设定/世界观.md",
  outline: "大纲/总大纲.md",
  "opening-plan": "大纲/开篇设计.md",
};

export const DEFAULT_DOCUMENT_TREE: DocumentTreeNode[] = [
  {
    id: "folder-settings",
    label: "设定",
    type: "folder",
    path: "设定",
    children: [
      { id: "world-view", label: "世界观.md", type: "file", path: "设定/世界观.md" },
      { id: "characters", label: "人物设定.md", type: "file", path: "设定/人物设定.md" },
      { id: "factions", label: "势力关系.md", type: "file", path: "设定/势力关系.md" },
      { id: "foreshadowing", label: "伏笔与坑.md", type: "file", path: "设定/伏笔与坑.md" },
    ],
  },
  {
    id: "folder-outline",
    label: "大纲",
    type: "folder",
    path: "大纲",
    children: [
      { id: "main-outline", label: "总大纲.md", type: "file", path: "大纲/总大纲.md" },
      { id: "opening-design", label: "开篇设计.md", type: "file", path: "大纲/开篇设计.md" },
      { id: "chapter-plan", label: "章节规划.md", type: "file", path: "大纲/章节规划.md" },
    ],
  },
  {
    id: "folder-content",
    label: "正文",
    type: "folder",
    path: "正文",
    children: [],
  },
  {
    id: "folder-appendix",
    label: "附录",
    type: "folder",
    path: "附录",
    children: [
      { id: "inspiration", label: "灵感碎片.md", type: "file", path: "附录/灵感碎片.md" },
    ],
  },
];

export function buildDocumentTreeFromChapters(chapters: ChapterSummary[]): DocumentTreeNode[] {
  const contentFolder = DEFAULT_DOCUMENT_TREE.find((node) => node.id === "folder-content");
  if (!contentFolder) {
    return DEFAULT_DOCUMENT_TREE;
  }
  const chapterNodes: DocumentTreeNode[] = chapters.map((chapter) => ({
    id: `chapter-${chapter.content_id}`,
    label: `第${String(chapter.chapter_number).padStart(3, "0")}章.md`,
    type: "file" as const,
    path: `正文/第${String(chapter.chapter_number).padStart(3, "0")}章.md`,
    icon: chapter.status === "stale" ? "stale" : undefined,
  }));
  contentFolder.children = chapterNodes;
  return DEFAULT_DOCUMENT_TREE;
}

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
  return STUDIO_PANEL_OPTIONS.find((item) => item.key === panel)?.label ?? "设定";
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
    : "setting";
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

export function findNodeByPath(tree: DocumentTreeNode[], path: string): DocumentTreeNode | null {
  for (const node of tree) {
    if (node.path === path) {
      return node;
    }
    if (node.children) {
      const found = findNodeByPath(node.children, path);
      if (found) {
        return found;
      }
    }
  }
  return null;
}
