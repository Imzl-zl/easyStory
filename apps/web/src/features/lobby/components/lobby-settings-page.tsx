"use client";

import { useCallback, useEffect, useTransition } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  isValidCredentialCenterMode,
  isValidCredentialCenterScope,
  normalizeCredentialSettingsPath,
  resolveCredentialCenterMode,
  resolveCredentialCenterScope,
} from "@/features/lobby/components/lobby-settings-support";
import { CredentialCenter } from "@/features/settings/components/credential-center";
import { normalizeOptionalQueryValue } from "@/features/settings/components/credential-center-support";

export function LobbySettingsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const routeMode = searchParams.get("sub");
  const routeScope = searchParams.get("scope");
  const routeProjectId = searchParams.get("project");
  const routeCredentialId = searchParams.get("credential");
  const mode = resolveCredentialCenterMode(routeMode);
  const projectId = normalizeOptionalQueryValue(routeProjectId);
  const scope = resolveCredentialCenterScope(routeScope, projectId);
  const credentialId = normalizeOptionalQueryValue(routeCredentialId);
  const currentSearch = searchParams.toString();

  const setParams = useCallback(
    (patches: Record<string, string | null>) => {
      startTransition(() => {
        router.replace(normalizeCredentialSettingsPath(pathname, currentSearch, patches));
      });
    },
    [currentSearch, pathname, router],
  );

  useEffect(() => {
    const hasInvalidMode = routeMode !== null && !isValidCredentialCenterMode(routeMode);
    const hasInvalidScope =
      (routeScope !== null && !isValidCredentialCenterScope(routeScope)) ||
      (routeScope === "project" && projectId === null);
    const hasUnnormalizedProjectId = routeProjectId !== projectId;
    const hasUnnormalizedCredentialId = routeCredentialId !== credentialId;
    if (
      !hasInvalidMode &&
      !hasInvalidScope &&
      !hasUnnormalizedProjectId &&
      !hasUnnormalizedCredentialId
    ) {
      return;
    }
    setParams({
      credential: hasUnnormalizedCredentialId ? credentialId : routeCredentialId,
      project: hasUnnormalizedProjectId ? projectId : routeProjectId,
      scope: hasInvalidScope ? scope : routeScope,
      sub: hasInvalidMode ? mode : routeMode,
    });
  }, [
    credentialId,
    mode,
    projectId,
    routeCredentialId,
    routeMode,
    routeProjectId,
    routeScope,
    scope,
    setParams,
  ]);

  return (
    <CredentialCenter
      headerAction={<Link className="ink-button-secondary" href="/workspace/lobby">返回 Lobby</Link>}
      isNavigationPending={isPending}
      mode={mode}
      projectId={projectId}
      scope={scope}
      selectedCredentialId={credentialId}
      onModeChange={(nextMode) =>
        setParams({
          credential: nextMode === "audit" ? credentialId : null,
          scope,
          sub: nextMode,
        })
      }
      onScopeChange={(nextScope) =>
        setParams({
          credential: null,
          scope: nextScope,
          sub: mode,
        })
      }
      onSelectCredential={(nextCredentialId) =>
        setParams({
          credential: nextCredentialId,
          scope,
          sub: "audit",
        })
      }
      onSelectCredentialForEdit={(nextCredentialId) =>
        setParams({
          credential: nextCredentialId,
          scope,
          sub: "list",
        })
      }
      onResetEditor={() =>
        setParams({
          credential: null,
          scope,
          sub: "list",
        })
      }
    />
  );
}
