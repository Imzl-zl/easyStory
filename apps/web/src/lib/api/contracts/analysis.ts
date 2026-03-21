import type { JsonValue } from "@/lib/api/contracts/base";

export type AnalysisType = "plot" | "character" | "style" | "pacing" | "structure";

export type AnalysisCreatePayload = {
  content_id?: string | null;
  analysis_type: AnalysisType;
  source_title?: string | null;
  analysis_scope?: Record<string, JsonValue> | null;
  result: Record<string, JsonValue>;
  suggestions?: Record<string, JsonValue> | null;
  generated_skill_key?: string | null;
};

export type AnalysisSummary = {
  id: string;
  project_id: string;
  content_id: string | null;
  analysis_type: AnalysisType;
  source_title: string | null;
  generated_skill_key: string | null;
  created_at: string;
};

export type AnalysisDetail = AnalysisSummary & {
  analysis_scope: Record<string, JsonValue> | null;
  result: Record<string, JsonValue>;
  suggestions: Record<string, JsonValue> | null;
};
