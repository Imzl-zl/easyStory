import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import type {
  AnalysisCreatePayload,
  AnalysisDetail,
  AnalysisSummary,
  AnalysisType,
  JsonValue,
} from "@/lib/api/types";

export const LAB_ANALYSIS_FILTER_ALL = "all";
export const LAB_ANALYSIS_TYPES: AnalysisType[] = ["plot", "character", "style", "pacing", "structure"];

export type LabAnalysisFilterState = {
  analysisType: AnalysisType | typeof LAB_ANALYSIS_FILTER_ALL;
  contentId: string;
  generatedSkillKey: string;
};

export type LabAnalysisListOptions = {
  analysisType?: AnalysisType;
  contentId?: string;
  generatedSkillKey?: string;
};

export type LabAnalysisFormState = {
  analysisType: AnalysisType;
  generatedSkillKey: string;
  result: string;
  sourceTitle: string;
  suggestions: string;
};

export type LabFeedback = {
  message: string;
  tone: "info" | "danger";
} | null;

export function createInitialLabAnalysisFilterState(): LabAnalysisFilterState {
  return {
    analysisType: LAB_ANALYSIS_FILTER_ALL,
    contentId: "",
    generatedSkillKey: "",
  };
}

export function createInitialLabAnalysisFormState(): LabAnalysisFormState {
  return {
    analysisType: "plot",
    generatedSkillKey: "",
    result: '{\n  "summary": ""\n}',
    sourceTitle: "",
    suggestions: '{\n  "next_step": ""\n}',
  };
}

export function buildLabAnalysisListOptions(
  filters: LabAnalysisFilterState,
): LabAnalysisListOptions {
  return {
    analysisType: filters.analysisType === LAB_ANALYSIS_FILTER_ALL ? undefined : filters.analysisType,
    contentId: normalizeOptionalText(filters.contentId),
    generatedSkillKey: normalizeOptionalText(filters.generatedSkillKey),
  };
}

export function buildLabAnalysisQueryKey(
  projectId: string,
  options: LabAnalysisListOptions,
) {
  return [
    "analyses",
    projectId,
    options.analysisType ?? null,
    options.contentId ?? null,
    options.generatedSkillKey ?? null,
  ] as const;
}

export function hasActiveLabAnalysisFilters(filters: LabAnalysisFilterState): boolean {
  return hasActiveLabAnalysisListOptions(buildLabAnalysisListOptions(filters));
}

export function hasActiveLabAnalysisListOptions(options: LabAnalysisListOptions): boolean {
  return Boolean(options.analysisType || options.contentId || options.generatedSkillKey);
}

export function matchesLabAnalysisListOptions(
  analysis: Pick<AnalysisSummary, "analysis_type" | "content_id" | "generated_skill_key">,
  options: LabAnalysisListOptions,
): boolean {
  if (options.analysisType && analysis.analysis_type !== options.analysisType) {
    return false;
  }
  if (options.contentId && analysis.content_id !== options.contentId) {
    return false;
  }
  if (options.generatedSkillKey && analysis.generated_skill_key !== options.generatedSkillKey) {
    return false;
  }
  return true;
}

export function resolveActiveLabAnalysisId(
  analyses: AnalysisSummary[] | undefined,
  selectedId: string | null,
): string | null {
  if (!analyses || analyses.length === 0) {
    return null;
  }
  if (selectedId && analyses.some((analysis) => analysis.id === selectedId)) {
    return selectedId;
  }
  return analyses[0]?.id ?? null;
}

export function resolveNextLabSelectedIdAfterDelete(
  analyses: AnalysisSummary[] | undefined,
  selectedId: string | null,
  deletedId: string,
): string | null {
  const currentAnalyses = analyses ?? [];
  const remainingAnalyses = removeLabAnalysisSummary(currentAnalyses, deletedId);
  if (remainingAnalyses.length === 0) {
    return null;
  }
  if (selectedId && selectedId !== deletedId) {
    return resolveActiveLabAnalysisId(remainingAnalyses, selectedId);
  }
  const deletedIndex = currentAnalyses.findIndex((analysis) => analysis.id === deletedId);
  const fallbackIndex = deletedIndex < 0 ? 0 : Math.min(deletedIndex, remainingAnalyses.length - 1);
  return remainingAnalyses[fallbackIndex]?.id ?? null;
}

export function buildLabCreatePayload(
  formState: LabAnalysisFormState,
): AnalysisCreatePayload {
  const sourceTitle = normalizeOptionalText(formState.sourceTitle);
  if (!sourceTitle) {
    throw new Error("来源标题不能为空。");
  }
  const result = parseRequiredJsonObject(formState.result, "result");
  if (Object.keys(result).length === 0) {
    throw new Error("result 不能为空。");
  }
  return {
    analysis_type: formState.analysisType,
    generated_skill_key: normalizeOptionalText(formState.generatedSkillKey) ?? null,
    result,
    source_title: sourceTitle,
    suggestions: parseOptionalJsonObject(formState.suggestions, "suggestions") ?? null,
  };
}

export function formatLabAnalysisTitle(
  analysis: Pick<AnalysisSummary, "analysis_type" | "source_title">,
): string {
  return analysis.source_title ?? analysis.analysis_type;
}

export function formatLabAnalysisTime(value: string): string {
  return formatObservabilityDateTime(value);
}

export function buildLabAnalysisSummary(
  analysis: Pick<
    AnalysisSummary | AnalysisDetail,
    "analysis_type" | "content_id" | "created_at" | "generated_skill_key" | "id" | "project_id" | "source_title"
  >,
): AnalysisSummary {
  return {
    analysis_type: analysis.analysis_type,
    content_id: analysis.content_id,
    created_at: analysis.created_at,
    generated_skill_key: analysis.generated_skill_key,
    id: analysis.id,
    project_id: analysis.project_id,
    source_title: analysis.source_title,
  };
}

export function prependLabAnalysisSummary(
  analyses: AnalysisSummary[] | undefined,
  analysis: AnalysisSummary,
): AnalysisSummary[] {
  return [analysis, ...(analyses ?? []).filter((item) => item.id !== analysis.id)];
}

export function removeLabAnalysisSummary(
  analyses: AnalysisSummary[] | undefined,
  analysisId: string,
): AnalysisSummary[] {
  return (analyses ?? []).filter((analysis) => analysis.id !== analysisId);
}

export function buildLabFeedback(
  message: string,
  tone: "info" | "danger" = "info",
): LabFeedback {
  return { message, tone };
}

function normalizeOptionalText(value: string): string | undefined {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
}

function parseOptionalJsonObject(
  value: string,
  fieldName: string,
): Record<string, JsonValue> | undefined {
  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }
  return parseRequiredJsonObject(normalized, fieldName);
}

function parseRequiredJsonObject(
  value: string,
  fieldName: string,
): Record<string, JsonValue> {
  const parsed = JSON.parse(value) as JsonValue;
  if (!isJsonObject(parsed)) {
    throw new Error(`${fieldName} 必须是 JSON object。`);
  }
  return parsed;
}

function isJsonObject(value: JsonValue): value is Record<string, JsonValue> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
