import type { ChapterSummary } from "@/lib/api/types";

export type StudioPanelKey = "setting" | "outline" | "opening-plan" | "chapter";
export type StudioChapterListState = "loading" | "error" | "empty" | "ready";

const STUDIO_PANEL_OPTIONS: Array<{
  key: StudioPanelKey;
  label: string;
}> = [
  { key: "setting", label: "设定" },
  { key: "outline", label: "大纲" },
  { key: "opening-plan", label: "开篇设计" },
  { key: "chapter", label: "章节" },
];

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
