"use client";

import type { QueryClient } from "@tanstack/react-query";

import {
  getChapter,
  getOpeningPlan,
  getOutline,
  saveChapter,
  saveOpeningPlan,
  saveOutline,
} from "@/lib/api/content";
import { getProjectDocument, saveProjectDocument } from "@/lib/api/projects";
import type {
  ChapterImpactSummary,
  StoryAssetImpactSummary,
} from "@/lib/api/contracts/project";
import { invalidateChapterQueries } from "@/features/studio/components/chapter-editor-support";
import { invalidateStoryAssetQueries } from "@/features/studio/components/story-asset-editor-support";

const OUTLINE_DOCUMENT_PATH = "大纲/总大纲.md";
const OPENING_PLAN_DOCUMENT_PATH = "大纲/开篇设计.md";
const CHAPTER_DOCUMENT_PATH = /^正文\/第(\d{3})章\.md$/;

type StudioDocumentTarget =
  | { kind: "file"; path: string }
  | { kind: "outline"; path: typeof OUTLINE_DOCUMENT_PATH }
  | { kind: "opening_plan"; path: typeof OPENING_PLAN_DOCUMENT_PATH }
  | { chapterNumber: number; kind: "chapter"; path: string };

export type StudioLoadedDocument = {
  content: string;
  path: string;
  saveNoun: "文稿" | "文件";
  storageKind: "database" | "file";
  target: StudioDocumentTarget;
  title: string;
};

type StudioSavedDocument = StudioLoadedDocument & {
  impact?: ChapterImpactSummary | StoryAssetImpactSummary;
};

export function resolveStudioDocumentTarget(documentPath: string | null): StudioDocumentTarget | null {
  if (!documentPath) {
    return null;
  }
  if (documentPath === OUTLINE_DOCUMENT_PATH) {
    return { kind: "outline", path: documentPath };
  }
  if (documentPath === OPENING_PLAN_DOCUMENT_PATH) {
    return { kind: "opening_plan", path: documentPath };
  }
  const matched = documentPath.match(CHAPTER_DOCUMENT_PATH);
  if (matched) {
    return {
      chapterNumber: Number(matched[1]),
      kind: "chapter",
      path: documentPath,
    };
  }
  return { kind: "file", path: documentPath };
}

export function buildStudioDocumentQueryKey(projectId: string, documentPath: string | null) {
  return ["studio-document", projectId, documentPath] as const;
}

export async function loadStudioDocument(
  projectId: string,
  target: StudioDocumentTarget,
): Promise<StudioLoadedDocument> {
  if (target.kind === "outline") {
    const outline = await getOutline(projectId);
    return {
      content: outline.content_text,
      path: target.path,
      saveNoun: "文稿",
      storageKind: "database",
      target,
      title: outline.title,
    };
  }
  if (target.kind === "opening_plan") {
    const openingPlan = await getOpeningPlan(projectId);
    return {
      content: openingPlan.content_text,
      path: target.path,
      saveNoun: "文稿",
      storageKind: "database",
      target,
      title: openingPlan.title,
    };
  }
  if (target.kind === "chapter") {
    const chapter = await getChapter(projectId, target.chapterNumber);
    return {
      content: chapter.content_text,
      path: target.path,
      saveNoun: "文稿",
      storageKind: "database",
      target,
      title: chapter.title,
    };
  }
  const document = await getProjectDocument(projectId, target.path);
  return {
    content: document.content,
    path: target.path,
    saveNoun: "文件",
    storageKind: "file",
    target,
    title: resolveDocumentTitle(target.path),
  };
}

export async function saveStudioDocument(
  projectId: string,
  document: StudioLoadedDocument,
  content: string,
): Promise<StudioSavedDocument> {
  const target = document.target;
  if (target.kind === "outline") {
    const saved = await saveOutline(projectId, {
      change_source: "user_edit",
      content_text: content,
      created_by: "user",
      title: document.title,
    });
    return {
      content: saved.content_text,
      impact: saved.impact,
      path: target.path,
      saveNoun: "文稿",
      storageKind: "database",
      target,
      title: saved.title,
    };
  }
  if (target.kind === "opening_plan") {
    const saved = await saveOpeningPlan(projectId, {
      change_source: "user_edit",
      content_text: content,
      created_by: "user",
      title: document.title,
    });
    return {
      content: saved.content_text,
      impact: saved.impact,
      path: target.path,
      saveNoun: "文稿",
      storageKind: "database",
      target,
      title: saved.title,
    };
  }
  if (target.kind === "chapter") {
    const saved = await saveChapter(projectId, target.chapterNumber, {
      change_source: "user_edit",
      content_text: content,
      created_by: "user",
      title: document.title,
    });
    return {
      content: saved.content_text,
      impact: saved.impact,
      path: target.path,
      saveNoun: "文稿",
      storageKind: "database",
      target,
      title: saved.title,
    };
  }
  const saved = await saveProjectDocument(projectId, target.path, { content });
  return {
    content: saved.content,
    path: target.path,
    saveNoun: "文件",
    storageKind: "file",
    target,
    title: resolveDocumentTitle(target.path),
  };
}

export function syncStudioDocumentQueries(
  queryClient: QueryClient,
  projectId: string,
  document: StudioSavedDocument,
) {
  queryClient.setQueryData(
    buildStudioDocumentQueryKey(projectId, document.path),
    document,
  );
  if (document.target.kind === "outline" || document.target.kind === "opening_plan") {
    invalidateStoryAssetQueries(queryClient, projectId, document.target.kind, document.impact ?? {
      has_impact: false,
      items: [],
      total_affected_entries: 0,
    });
    return;
  }
  if (document.target.kind === "chapter") {
    invalidateChapterQueries(queryClient, projectId, document.target.chapterNumber);
  }
}

function resolveDocumentTitle(documentPath: string) {
  const parts = documentPath.split("/");
  return parts.at(-1)?.replace(/\.md$/i, "") ?? "未命名文稿";
}
