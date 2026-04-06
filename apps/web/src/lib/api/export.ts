import { ApiError, createApiErrorFromPayload, getApiBaseUrl, requestJson } from "@/lib/api/client";
import type { ExportCreatePayload, ExportView } from "@/lib/api/types";
import { getAuthToken } from "@/lib/stores/auth-store";

export function listProjectExports(projectId: string) {
  return requestJson<ExportView[]>(`/api/v1/projects/${projectId}/exports`);
}

export function createWorkflowExports(workflowId: string, payload: ExportCreatePayload) {
  return requestJson<ExportView[]>(`/api/v1/workflows/${workflowId}/exports`, {
    method: "POST",
    body: payload,
  });
}

export function getExportDownloadUrl(exportId: string): string {
  return `${getApiBaseUrl()}/api/v1/exports/${exportId}/download`;
}

export async function downloadExportFile(exportItem: Pick<ExportView, "id" | "filename">) {
  const token = getAuthToken();
  if (!token) {
    throw new ApiError("当前会话已失效，请重新登录。", 401, null);
  }

  const response = await fetch(getExportDownloadUrl(exportItem.id), {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await toDownloadError(response);
  }

  const downloadUrl = URL.createObjectURL(await response.blob());
  triggerBrowserDownload(downloadUrl, exportItem.filename);
}

async function toDownloadError(response: Response): Promise<ApiError> {
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  return createApiErrorFromPayload(payload, response.status);
}

function triggerBrowserDownload(downloadUrl: string, filename: string) {
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);
}
