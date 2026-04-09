import type { CredentialView } from "@/lib/api/types";
import {
  createCredentialFormFromView,
  createInitialCredentialForm,
} from "@/features/settings/components/credential/credential-center-form-support";

export {
  AUTH_STRATEGY_OPTIONS,
  getInteropProfileOptions,
  getDefaultAuthStrategy,
  sanitizeCredentialInteropProfileSelection,
  supportsCredentialInteropProfile,
  type CredentialAuthStrategyValue,
  type CredentialInteropProfileValue,
} from "@/features/settings/components/credential/credential-center-compatibility-support";
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
} from "@/features/settings/components/credential/credential-center-form-support";

export type CredentialCenterMode = "list" | "audit";

type ResolveCredentialEditorStateOptions = {
  createFormVersion: number;
  editFormVersion: number;
  editableCredential: CredentialView | null;
  savedEditableCredential: CredentialView | null;
  scope: "user" | "project";
  scopedProjectId: string | null;
};

export function resolveCredentialEditorState({
  createFormVersion,
  editFormVersion,
  editableCredential,
  savedEditableCredential,
  scope,
  scopedProjectId,
}: Readonly<ResolveCredentialEditorStateOptions>) {
  if (editableCredential) {
    const baselineCredential = (
      savedEditableCredential && savedEditableCredential.id === editableCredential.id
    )
      ? savedEditableCredential
      : editableCredential;
    return {
      activeFormKey: `edit:${editableCredential.id}:${editFormVersion}`,
      activeInitialState: createCredentialFormFromView(baselineCredential),
    };
  }
  return {
    activeFormKey: `create:${scope}:${scopedProjectId ?? "global"}:${createFormVersion}`,
    activeInitialState: createInitialCredentialForm(),
  };
}

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
