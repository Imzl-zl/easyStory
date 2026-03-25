import type {
  CredentialCenterMode,
  CredentialCenterScope,
} from "@/features/settings/components/credential-center-support";

const CREDENTIAL_CENTER_MODES: CredentialCenterMode[] = ["list", "audit"];
const CREDENTIAL_CENTER_SCOPES: CredentialCenterScope[] = ["user", "project"];

export function resolveCredentialCenterMode(value: string | null): CredentialCenterMode {
  return CREDENTIAL_CENTER_MODES.includes(value as CredentialCenterMode)
    ? (value as CredentialCenterMode)
    : "list";
}

export function isValidCredentialCenterMode(value: string | null): value is CredentialCenterMode {
  return CREDENTIAL_CENTER_MODES.includes(value as CredentialCenterMode);
}

export function resolveCredentialCenterScope(
  value: string | null,
  projectId: string | null,
): CredentialCenterScope {
  if (value === "project" && projectId) {
    return "project";
  }
  return "user";
}

export function isValidCredentialCenterScope(value: string | null): value is CredentialCenterScope {
  return CREDENTIAL_CENTER_SCOPES.includes(value as CredentialCenterScope);
}

export function normalizeCredentialSettingsPath(pathname: string, currentSearch: string, patches: Record<string, string | null>) {
  const next = new URLSearchParams(currentSearch);
  next.set("tab", "credentials");
  Object.entries(patches).forEach(([key, value]) => {
    if (value === null) {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  const search = next.toString();
  return search ? `${pathname}?${search}` : pathname;
}
