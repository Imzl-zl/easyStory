import { requestJson } from "@/lib/api/client";
import type {
  AssistantSkillDetail,
  AssistantSkillPayload,
  AssistantSkillSummary,
} from "@/lib/api/types";

export function listMyAssistantSkills() {
  return requestJson<AssistantSkillSummary[]>("/api/v1/assistant/skills");
}

export function listProjectAssistantSkills(projectId: string) {
  return requestJson<AssistantSkillSummary[]>(`/api/v1/assistant/skills/projects/${projectId}`);
}

export function createMyAssistantSkill(payload: AssistantSkillPayload) {
  return requestJson<AssistantSkillDetail>("/api/v1/assistant/skills", {
    method: "POST",
    body: payload,
  });
}

export function createProjectAssistantSkill(
  projectId: string,
  payload: AssistantSkillPayload,
) {
  return requestJson<AssistantSkillDetail>(`/api/v1/assistant/skills/projects/${projectId}`, {
    method: "POST",
    body: payload,
  });
}

export function getMyAssistantSkill(skillId: string) {
  return requestJson<AssistantSkillDetail>(`/api/v1/assistant/skills/${skillId}`);
}

export function getProjectAssistantSkill(projectId: string, skillId: string) {
  return requestJson<AssistantSkillDetail>(
    `/api/v1/assistant/skills/projects/${projectId}/${skillId}`,
  );
}

export function updateMyAssistantSkill(skillId: string, payload: AssistantSkillPayload) {
  return requestJson<AssistantSkillDetail>(`/api/v1/assistant/skills/${skillId}`, {
    method: "PUT",
    body: payload,
  });
}

export function updateProjectAssistantSkill(
  projectId: string,
  skillId: string,
  payload: AssistantSkillPayload,
) {
  return requestJson<AssistantSkillDetail>(
    `/api/v1/assistant/skills/projects/${projectId}/${skillId}`,
    {
      method: "PUT",
      body: payload,
    },
  );
}

export function deleteMyAssistantSkill(skillId: string) {
  return requestJson<void>(`/api/v1/assistant/skills/${skillId}`, {
    method: "DELETE",
  });
}

export function deleteProjectAssistantSkill(projectId: string, skillId: string) {
  return requestJson<void>(`/api/v1/assistant/skills/projects/${projectId}/${skillId}`, {
    method: "DELETE",
  });
}
