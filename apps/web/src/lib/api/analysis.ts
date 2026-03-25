import { requestJson } from "@/lib/api/client";
import type { AnalysisCreatePayload, AnalysisDetail, AnalysisSummary, AnalysisType } from "@/lib/api/types";

export type AnalysisListOptions = {
  analysisType?: AnalysisType;
  contentId?: string;
  generatedSkillKey?: string;
};

export function listAnalyses(
  projectId: string,
  options: AnalysisListOptions = {},
) {
  const search = new URLSearchParams();
  if (options.analysisType) {
    search.set("analysis_type", options.analysisType);
  }
  if (options.contentId) {
    search.set("content_id", options.contentId);
  }
  if (options.generatedSkillKey) {
    search.set("generated_skill_key", options.generatedSkillKey);
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return requestJson<AnalysisSummary[]>(`/api/v1/projects/${projectId}/analyses${suffix}`);
}

export function createAnalysis(projectId: string, payload: AnalysisCreatePayload) {
  return requestJson<AnalysisDetail>(`/api/v1/projects/${projectId}/analyses`, {
    method: "POST",
    body: payload,
  });
}

export function getAnalysis(projectId: string, analysisId: string) {
  return requestJson<AnalysisDetail>(`/api/v1/projects/${projectId}/analyses/${analysisId}`);
}

export function deleteAnalysis(projectId: string, analysisId: string) {
  return requestJson<void>(`/api/v1/projects/${projectId}/analyses/${analysisId}`, {
    method: "DELETE",
  });
}
