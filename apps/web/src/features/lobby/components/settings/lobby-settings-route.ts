"use client";

import { useCallback, useEffect, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  isValidCredentialCenterMode,
  isValidCredentialCenterScope,
  isValidLobbySettingsTab,
  normalizeLobbySettingsPath,
  resolveCredentialCenterMode,
  resolveCredentialCenterScope,
  resolveLobbySettingsTab,
  type LobbySettingsTab,
} from "@/features/lobby/components/settings/lobby-settings-support";
import { normalizeOptionalQueryValue } from "@/features/settings/components/credential/credential-center-support";

export type LobbySettingsRouteState = {
  credentialId: string | null;
  currentSearch: string;
  isPending: boolean;
  mode: "audit" | "list";
  pathname: string;
  projectId: string | null;
  rawCredentialId: string | null;
  rawMode: string | null;
  rawProjectId: string | null;
  rawScope: string | null;
  rawTab: string | null;
  scope: "project" | "user";
  setParams: (patches: Record<string, string | null>) => void;
  tab: LobbySettingsTab;
};

export function useLobbySettingsRouteState(): LobbySettingsRouteState {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const rawMode = searchParams.get("sub");
  const rawTab = searchParams.get("tab");
  const rawScope = searchParams.get("scope");
  const rawProjectId = searchParams.get("project");
  const rawCredentialId = searchParams.get("credential");
  const currentSearch = searchParams.toString();
  const projectId = normalizeOptionalQueryValue(rawProjectId);

  return {
    credentialId: normalizeOptionalQueryValue(rawCredentialId),
    currentSearch,
    isPending,
    mode: resolveCredentialCenterMode(rawMode),
    pathname,
    projectId,
    rawCredentialId,
    rawMode,
    rawProjectId,
    rawScope,
    rawTab,
    scope: resolveCredentialCenterScope(rawScope, projectId),
    setParams: useCallback(
      (patches: Record<string, string | null>) => {
        startTransition(() => {
          router.replace(normalizeLobbySettingsPath(pathname, currentSearch, patches));
        });
      },
      [currentSearch, pathname, router],
    ),
    tab: resolveLobbySettingsTab(rawTab),
  };
}

export function useNormalizeLobbySettingsRoute(route: LobbySettingsRouteState) {
  useEffect(() => {
    const isCredentialTab = route.tab === "credentials";
    const hasInvalidTab = route.rawTab !== null && !isValidLobbySettingsTab(route.rawTab);
    const hasUnnormalizedTab = route.rawTab !== null && route.rawTab !== route.tab;
    const hasInvalidMode = isCredentialTab
      && route.rawMode !== null
      && !isValidCredentialCenterMode(route.rawMode);
    const hasInvalidScope = isCredentialTab
      && ((route.rawScope !== null && !isValidCredentialCenterScope(route.rawScope))
        || (route.rawScope === "project" && route.projectId === null));
    const hasUnnormalizedProjectId = isCredentialTab && route.rawProjectId !== route.projectId;
    const hasUnnormalizedCredentialId = isCredentialTab && route.rawCredentialId !== route.credentialId;
    const hasAssistantNoise = !isCredentialTab && (
      route.rawMode !== null
      || route.rawScope !== null
      || route.rawProjectId !== null
      || route.rawCredentialId !== null
    );

    if (
      !hasInvalidTab
      && !hasUnnormalizedTab
      && !hasInvalidMode
      && !hasInvalidScope
      && !hasUnnormalizedProjectId
      && !hasUnnormalizedCredentialId
      && !hasAssistantNoise
    ) {
      return;
    }

    route.setParams({
      credential: isCredentialTab
        ? (hasUnnormalizedCredentialId ? route.credentialId : route.rawCredentialId)
        : null,
      project: isCredentialTab
        ? (hasUnnormalizedProjectId ? route.projectId : route.rawProjectId)
        : null,
      scope: isCredentialTab ? (hasInvalidScope ? route.scope : route.rawScope) : null,
      sub: isCredentialTab ? (hasInvalidMode ? route.mode : route.rawMode) : null,
      tab: hasInvalidTab || hasUnnormalizedTab ? route.tab : route.rawTab,
    });
  }, [route]);
}
