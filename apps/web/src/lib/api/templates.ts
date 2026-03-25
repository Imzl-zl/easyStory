import { requestJson } from "@/lib/api/client";
import type { TemplateDetail, TemplateSummary, TemplateUpsertPayload } from "@/lib/api/types";

export function listTemplates() {
  return requestJson<TemplateSummary[]>("/api/v1/templates");
}

export function getTemplate(templateId: string) {
  return requestJson<TemplateDetail>(`/api/v1/templates/${templateId}`);
}

export function createTemplate(payload: TemplateUpsertPayload) {
  return requestJson<TemplateDetail>("/api/v1/templates", {
    method: "POST",
    body: payload,
  });
}

export function updateTemplate(templateId: string, payload: TemplateUpsertPayload) {
  return requestJson<TemplateDetail>(`/api/v1/templates/${templateId}`, {
    method: "PUT",
    body: payload,
  });
}

export async function deleteTemplate(templateId: string) {
  await requestJson<string>(`/api/v1/templates/${templateId}`, {
    method: "DELETE",
  });
}
