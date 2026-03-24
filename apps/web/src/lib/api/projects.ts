import { requestJson } from "@/lib/api/client";
import type {
  ProjectCreatePayload,
  ProjectDetail,
  ProjectPreparationStatus,
  ProjectSetting,
  ProjectSettingSnapshot,
  ProjectSummary,
  SettingCompletenessResult,
} from "@/lib/api/types";

export function listProjects(deletedOnly = false) {
  const search = deletedOnly ? "?deleted_only=true" : "";
  return requestJson<ProjectSummary[]>(`/api/v1/projects${search}`);
}

export function createProject(payload: ProjectCreatePayload) {
  return requestJson<ProjectDetail>("/api/v1/projects", {
    method: "POST",
    body: payload,
  });
}

export function getProject(projectId: string) {
  return requestJson<ProjectDetail>(`/api/v1/projects/${projectId}`);
}

export function deleteProject(projectId: string) {
  return requestJson<ProjectDetail>(`/api/v1/projects/${projectId}`, {
    method: "DELETE",
  });
}

export function restoreProject(projectId: string) {
  return requestJson<ProjectDetail>(`/api/v1/projects/${projectId}/restore`, {
    method: "POST",
  });
}

export function updateProjectSetting(projectId: string, projectSetting: ProjectSetting) {
  return requestJson<ProjectSettingSnapshot>(`/api/v1/projects/${projectId}/setting`, {
    method: "PUT",
    body: { project_setting: projectSetting },
  });
}

export function checkProjectSetting(projectId: string) {
  return requestJson<SettingCompletenessResult>(
    `/api/v1/projects/${projectId}/setting/complete-check`,
    { method: "POST" },
  );
}

export function getProjectPreparationStatus(projectId: string) {
  return requestJson<ProjectPreparationStatus>(`/api/v1/projects/${projectId}/preparation/status`);
}
