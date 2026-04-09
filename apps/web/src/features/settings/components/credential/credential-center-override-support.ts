import type { CredentialView } from "@/lib/api/types";

export type CredentialOverrideInfo = {
  projectCredentialDisplayName: string;
  projectCredentialId: string;
  provider: string;
};

export function buildCredentialOverrideInfoByCredentialId(
  userCredentials: CredentialView[] | undefined,
  projectCredentials: CredentialView[] | undefined,
): Record<string, CredentialOverrideInfo> {
  if (!userCredentials || !projectCredentials || projectCredentials.length === 0) {
    return {};
  }
  const activeProjectCredentialByProvider = new Map(
    projectCredentials
      .filter((credential) => credential.is_active)
      .map((credential) => [
        credential.provider,
        {
          projectCredentialDisplayName: credential.display_name,
          projectCredentialId: credential.id,
          provider: credential.provider,
        } satisfies CredentialOverrideInfo,
      ]),
  );
  return Object.fromEntries(
    userCredentials.flatMap((credential) => {
      if (!credential.is_active) {
        return [];
      }
      const override = activeProjectCredentialByProvider.get(credential.provider);
      return override ? [[credential.id, override]] : [];
    }),
  );
}
