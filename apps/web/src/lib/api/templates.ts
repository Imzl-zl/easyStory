import { requestJson } from "@/lib/api/client";
import type { TemplateDetail, TemplateSummary } from "@/lib/api/types";

export function listTemplates() {
  return requestJson<TemplateSummary[]>("/api/v1/templates");
}

export function getTemplate(templateId: string) {
  return requestJson<TemplateDetail>(`/api/v1/templates/${templateId}`);
}
