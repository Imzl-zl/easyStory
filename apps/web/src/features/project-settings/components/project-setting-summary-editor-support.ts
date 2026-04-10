"use client";

import type { QueryClient } from "@tanstack/react-query";

import {
  getMyAssistantPreferences,
  getProjectAssistantPreferences,
} from "@/lib/api/assistant";
import { listCredentials } from "@/lib/api/credential";
import type {
  AssistantPreferences,
  ProjectSettingImpactSummary,
} from "@/lib/api/types";
import { buildIncubatorCredentialOptions } from "@/features/shared/assistant/assistant-credential-support";

export type ProjectSettingSummaryEditorResources = {
  credentialOptions: ReturnType<typeof buildIncubatorCredentialOptions>;
  projectPreferences: AssistantPreferences;
  userPreferences: AssistantPreferences;
};

export const PROJECT_SETTING_SUMMARY_SOURCE_DOCUMENT_PATH = "项目说明.md";

const EMPTY_PREFERENCES: AssistantPreferences = {
  default_max_output_tokens: null,
  default_model_name: null,
  default_provider: null,
  default_reasoning_effort: null,
  default_thinking_level: null,
  default_thinking_budget: null,
};

export function buildProjectSettingSummarySaveFeedback(impact: ProjectSettingImpactSummary) {
  if (!impact.has_impact) {
    return "项目摘要已保存，当前没有需要重新标记的下游内容。";
  }
  return `项目摘要已保存，并同步标记 ${impact.total_affected_entries} 个下游项为 stale。`;
}

export function normalizeProjectSettingSummarySourceContent(
  content: string | null | undefined,
) {
  return content?.trim() ?? "";
}

export function buildProjectSettingSummarySourceExcerpt(
  content: string | null | undefined,
  maxLength = 220,
) {
  const normalized = normalizeProjectSettingSummarySourceContent(content).replace(/\s+/g, " ");
  if (!normalized) {
    return "";
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength).trimEnd()}…`;
}

export function invalidateProjectSettingSummaryQueries(
  queryClient: QueryClient,
  projectId: string,
  impact: ProjectSettingImpactSummary,
) {
  queryClient.invalidateQueries({ queryKey: ["project", projectId] });
  queryClient.invalidateQueries({ queryKey: ["setting-check", projectId] });
  queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
  if (impact.items.some((item) => item.target === "outline")) {
    queryClient.invalidateQueries({ queryKey: ["story-asset", projectId, "outline"] });
  }
  if (impact.items.some((item) => item.target === "opening_plan")) {
    queryClient.invalidateQueries({ queryKey: ["story-asset", projectId, "opening_plan"] });
  }
  if (impact.items.some((item) => item.target === "chapter")) {
    queryClient.invalidateQueries({ queryKey: ["chapters", projectId] });
  }
}

export async function loadProjectSettingSummaryEditorResources(
  projectId: string,
): Promise<ProjectSettingSummaryEditorResources> {
  const [projectCredentials, userCredentials, projectPreferences, userPreferences] =
    await Promise.all([
      listCredentials("project", projectId),
      listCredentials("user"),
      getProjectAssistantPreferences(projectId).catch(() => EMPTY_PREFERENCES),
      getMyAssistantPreferences().catch(() => EMPTY_PREFERENCES),
    ]);
  return {
    credentialOptions: buildIncubatorCredentialOptions([
      ...projectCredentials,
      ...userCredentials,
    ]),
    projectPreferences,
    userPreferences,
  };
}

export function buildProjectSettingSummaryProviderOptions(
  credentials: ProjectSettingSummaryEditorResources["credentialOptions"],
) {
  return credentials.map((credential) => ({
    description: credential.displayLabel,
    label: credential.provider,
    value: credential.provider,
  }));
}

export function resolveProjectSettingSummaryPreferredProvider(
  resources: ProjectSettingSummaryEditorResources | undefined,
) {
  return resources?.projectPreferences.default_provider?.trim()
    || resources?.userPreferences.default_provider?.trim()
    || "";
}

export function resolveProjectSettingSummaryPreferredModelName(
  resources: ProjectSettingSummaryEditorResources | undefined,
  provider: string,
) {
  if (!provider.trim() || !resources) {
    return "";
  }
  if (resources.projectPreferences.default_provider?.trim() === provider.trim()) {
    return resources.projectPreferences.default_model_name?.trim() ?? "";
  }
  if (resources.userPreferences.default_provider?.trim() === provider.trim()) {
    return resources.userPreferences.default_model_name?.trim() ?? "";
  }
  return "";
}
