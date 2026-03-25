import { requestJson } from "@/lib/api/client";
import type {
  CredentialCreatePayload,
  CredentialUpdatePayload,
  CredentialVerifyResult,
  CredentialView,
} from "@/lib/api/types";

export function listCredentials(ownerType: "user" | "project", projectId?: string) {
  const search = new URLSearchParams({ owner_type: ownerType });
  if (projectId) {
    search.set("project_id", projectId);
  }
  return requestJson<CredentialView[]>(`/api/v1/credentials?${search.toString()}`);
}

export function createCredential(payload: CredentialCreatePayload) {
  return requestJson<CredentialView>("/api/v1/credentials", {
    method: "POST",
    body: payload,
  });
}

export function updateCredential(credentialId: string, payload: CredentialUpdatePayload) {
  return requestJson<CredentialView>(`/api/v1/credentials/${credentialId}`, {
    method: "PUT",
    body: payload,
  });
}

export function verifyCredential(credentialId: string) {
  return requestJson<CredentialVerifyResult>(`/api/v1/credentials/${credentialId}/verify`, {
    method: "POST",
  });
}

export function enableCredential(credentialId: string) {
  return requestJson<CredentialView>(`/api/v1/credentials/${credentialId}/enable`, {
    method: "POST",
  });
}

export function disableCredential(credentialId: string) {
  return requestJson<CredentialView>(`/api/v1/credentials/${credentialId}/disable`, {
    method: "POST",
  });
}

export function deleteCredential(credentialId: string) {
  return requestJson<void>(`/api/v1/credentials/${credentialId}`, {
    method: "DELETE",
  });
}
