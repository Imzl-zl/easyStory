import type {
  CredentialCenterMode,
  CredentialCenterScope,
} from "@/features/settings/components/credential-center-support";

export type LobbySettingsTab = "assistant" | "credentials";

const CREDENTIAL_CENTER_MODES: CredentialCenterMode[] = ["list", "audit"];
const CREDENTIAL_CENTER_SCOPES: CredentialCenterScope[] = ["user", "project"];
const LOBBY_SETTINGS_TAB_ALIASES = {
  assistant: "assistant",
  "assistant-preferences": "assistant",
  "assistant-rules": "assistant",
  credentials: "credentials",
} as const;

export function resolveLobbySettingsTab(value: string | null): LobbySettingsTab {
  if (value && value in LOBBY_SETTINGS_TAB_ALIASES) {
    return LOBBY_SETTINGS_TAB_ALIASES[value as keyof typeof LOBBY_SETTINGS_TAB_ALIASES];
  }
  return "assistant";
}

export function isValidLobbySettingsTab(value: string | null): boolean {
  return value !== null && value in LOBBY_SETTINGS_TAB_ALIASES;
}

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

export function normalizeLobbySettingsPath(
  pathname: string,
  currentSearch: string,
  patches: Record<string, string | null>,
) {
  const next = new URLSearchParams(currentSearch);
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

export function normalizeCredentialSettingsPath(
  pathname: string,
  currentSearch: string,
  patches: Record<string, string | null>,
) {
  return normalizeLobbySettingsPath(pathname, currentSearch, {
    ...patches,
    tab: "credentials",
  });
}
