import { requestJson } from "@/lib/api/client";
import type {
  ChapterDetail,
  ChapterSavePayload,
  ChapterSummary,
  ChapterVersion,
  StoryAsset,
  StoryAssetMutation,
  StoryAssetSavePayload,
} from "@/lib/api/types";

export function getOutline(projectId: string) {
  return requestJson<StoryAsset>(`/api/v1/projects/${projectId}/outline`);
}

export function saveOutline(projectId: string, payload: StoryAssetSavePayload) {
  return requestJson<StoryAssetMutation>(`/api/v1/projects/${projectId}/outline`, {
    method: "PUT",
    body: payload,
  });
}

export function approveOutline(projectId: string) {
  return requestJson<StoryAssetMutation>(`/api/v1/projects/${projectId}/outline/approve`, {
    method: "POST",
  });
}

export function getOpeningPlan(projectId: string) {
  return requestJson<StoryAsset>(`/api/v1/projects/${projectId}/opening-plan`);
}

export function saveOpeningPlan(projectId: string, payload: StoryAssetSavePayload) {
  return requestJson<StoryAssetMutation>(`/api/v1/projects/${projectId}/opening-plan`, {
    method: "PUT",
    body: payload,
  });
}

export function approveOpeningPlan(projectId: string) {
  return requestJson<StoryAssetMutation>(`/api/v1/projects/${projectId}/opening-plan/approve`, {
    method: "POST",
  });
}

export function listChapters(projectId: string) {
  return requestJson<ChapterSummary[]>(`/api/v1/projects/${projectId}/chapters`);
}

export function getChapter(projectId: string, chapterNumber: number) {
  return requestJson<ChapterDetail>(`/api/v1/projects/${projectId}/chapters/${chapterNumber}`);
}

export function saveChapter(
  projectId: string,
  chapterNumber: number,
  payload: ChapterSavePayload,
) {
  return requestJson<ChapterDetail>(`/api/v1/projects/${projectId}/chapters/${chapterNumber}`, {
    method: "PUT",
    body: payload,
  });
}

export function approveChapter(projectId: string, chapterNumber: number) {
  return requestJson<ChapterDetail>(
    `/api/v1/projects/${projectId}/chapters/${chapterNumber}/approve`,
    {
      method: "POST",
    },
  );
}

export function listChapterVersions(projectId: string, chapterNumber: number) {
  return requestJson<ChapterVersion[]>(
    `/api/v1/projects/${projectId}/chapters/${chapterNumber}/versions`,
  );
}

export function rollbackChapterVersion(
  projectId: string,
  chapterNumber: number,
  versionNumber: number,
) {
  return requestJson<ChapterDetail>(
    `/api/v1/projects/${projectId}/chapters/${chapterNumber}/versions/${versionNumber}/rollback`,
    {
      method: "POST",
    },
  );
}

export function markBestVersion(projectId: string, chapterNumber: number, versionNumber: number) {
  return requestJson<ChapterVersion>(
    `/api/v1/projects/${projectId}/chapters/${chapterNumber}/versions/${versionNumber}/best`,
    {
      method: "POST",
    },
  );
}

export function clearBestVersion(
  projectId: string,
  chapterNumber: number,
  versionNumber: number,
) {
  return requestJson<ChapterVersion>(
    `/api/v1/projects/${projectId}/chapters/${chapterNumber}/versions/${versionNumber}/best`,
    {
      method: "DELETE",
    },
  );
}
