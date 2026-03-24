import type { ChapterSummary } from "@/lib/api/types";

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
