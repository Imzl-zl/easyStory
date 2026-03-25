"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { CredentialCenter } from "@/features/settings/components/credential-center";
import type { CredentialCenterMode } from "@/features/settings/components/credential-center-support";

export function LobbySettingsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const mode = resolveCredentialMode(searchParams.get("sub"));
  const credentialId = searchParams.get("credential");

  return (
    <CredentialCenter
      headerAction={<Link className="ink-button-secondary" href="/workspace/lobby">返回 Lobby</Link>}
      mode={mode}
      selectedCredentialId={credentialId}
      onModeChange={(nextMode) => setSettingsParams(router, pathname, searchParams, { sub: nextMode, credential: nextMode === "audit" ? credentialId : null })}
      onSelectCredential={(nextCredentialId) => setSettingsParams(router, pathname, searchParams, { sub: "audit", credential: nextCredentialId })}
    />
  );
}

function resolveCredentialMode(value: string | null): CredentialCenterMode {
  return value === "audit" ? "audit" : "list";
}

function setSettingsParams(
  router: ReturnType<typeof useRouter>,
  pathname: string,
  current: ReturnType<typeof useSearchParams>,
  next: {
    sub?: string | null;
    credential?: string | null;
  },
) {
  const params = new URLSearchParams(current.toString());
  params.set("tab", "credentials");
  updateSearchParam(params, "sub", next.sub ?? null);
  updateSearchParam(params, "credential", next.credential ?? null);
  router.push(`${pathname}?${params.toString()}`);
}

function updateSearchParam(params: URLSearchParams, key: string, value: string | null) {
  if (value) {
    params.set(key, value);
    return;
  }
  params.delete(key);
}
