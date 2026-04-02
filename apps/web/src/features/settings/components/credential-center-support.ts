import type { CredentialView } from "@/lib/api/types";

export {
  AUTH_STRATEGY_OPTIONS,
  getDefaultAuthStrategy,
  type CredentialAuthStrategyValue,
} from "@/features/settings/components/credential-center-compatibility-support";
export {
  API_DIALECT_OPTIONS,
  buildCredentialCreatePayload,
  buildCredentialUpdatePayload,
  createCredentialFormFromView,
  createInitialCredentialForm,
  formatCredentialBaseUrl,
  getApiDialectLabel,
  getCredentialUpdatePayloadSize,
  getDefaultBaseUrl,
  isCredentialFormDirty,
  normalizeCredentialBaseUrl,
  normalizeOptionalQueryValue,
  type CredentialCenterScope,
  type CredentialFormState,
} from "@/features/settings/components/credential-center-form-support";

export type CredentialCenterMode = "list" | "audit";

export function resolveActiveCredentialId(
  credentials: CredentialView[] | undefined,
  selectedCredentialId: string | null,
): string | null {
  if (!credentials || credentials.length === 0) {
    return null;
  }
  if (selectedCredentialId && credentials.some((credential) => credential.id === selectedCredentialId)) {
    return selectedCredentialId;
  }
  return credentials[0]?.id ?? null;
}

export function resolveEditableCredential(
  credentials: CredentialView[] | undefined,
  selectedCredentialId: string | null,
): CredentialView | null {
  if (!credentials || !selectedCredentialId) {
    return null;
  }
  return credentials.find((credential) => credential.id === selectedCredentialId) ?? null;
}
