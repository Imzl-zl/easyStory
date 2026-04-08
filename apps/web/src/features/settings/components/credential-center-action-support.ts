export type CredentialCenterActionType =
  | "verify_connection"
  | "verify_tools"
  | "enable"
  | "disable"
  | "delete";

export type PendingCredentialAction = Readonly<{
  credentialId: string;
  type: CredentialCenterActionType;
}>;

const ACTION_LABELS: Record<CredentialCenterActionType, string> = {
  verify_connection: "验证连接",
  verify_tools: "验证工具",
  enable: "启用",
  disable: "停用",
  delete: "删除",
};

const ACTION_PENDING_LABELS: Record<CredentialCenterActionType, string> = {
  verify_connection: "验证中...",
  verify_tools: "验证中...",
  enable: "启用中...",
  disable: "停用中...",
  delete: "删除中...",
};

export function resolvePendingCredentialAction(
  isPending: boolean,
  variables: PendingCredentialAction | undefined,
): PendingCredentialAction | null {
  if (!isPending || !variables) {
    return null;
  }
  return {
    credentialId: variables.credentialId,
    type: variables.type,
  };
}

export function isPendingCredentialAction(
  pendingAction: PendingCredentialAction | null,
  actionType: CredentialCenterActionType,
  credentialId: string,
): boolean {
  return pendingAction?.type === actionType && pendingAction.credentialId === credentialId;
}

export function resolveCredentialActionButtonLabel(
  actionType: CredentialCenterActionType,
  isPending: boolean,
): string {
  return isPending ? ACTION_PENDING_LABELS[actionType] : ACTION_LABELS[actionType];
}
