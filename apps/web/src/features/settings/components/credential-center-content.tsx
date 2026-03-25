"use client";

import { EmptyState } from "@/components/ui/empty-state";
import type { PendingCredentialAction } from "@/features/settings/components/credential-center-action-support";
import type { CredentialCenterFeedback } from "@/features/settings/components/credential-center-feedback";
import { CredentialCenterForm } from "@/features/settings/components/credential-center-form";
import { CredentialCenterList } from "@/features/settings/components/credential-center-list";
import type { CredentialOverrideInfo } from "@/features/settings/components/credential-center-override-support";
import { CredentialAuditPanel } from "@/features/settings/components/credential-audit-panel";
import type {
  CredentialCenterMode,
  CredentialFormState,
} from "@/features/settings/components/credential-center-support";
import { createInitialCredentialForm } from "@/features/settings/components/credential-center-support";
import type { CredentialView } from "@/lib/api/types";

type CredentialCenterContentProps = {
  activeAuditCredentialId: string | null;
  activeFormKey: string;
  activeInitialState: CredentialFormState;
  credentials: CredentialView[] | undefined;
  editableCredential: CredentialView | null;
  feedback: CredentialCenterFeedback;
  isFormPending: boolean;
  mode: CredentialCenterMode;
  overrideInfoByCredentialId: Record<string, CredentialOverrideInfo>;
  pendingAction: PendingCredentialAction | null;
  shouldShowEditLoadingState: boolean;
  onAction: (type: PendingCredentialAction["type"], credentialId: string) => void;
  onResetEditor?: () => void;
  onSelectCredential?: (credentialId: string | null) => void;
  onSelectCredentialForEdit?: (credentialId: string | null) => void;
  onSubmitCreate: (formState: CredentialFormState) => void;
  onSubmitUpdate: (credential: CredentialView, formState: CredentialFormState) => void;
};

export function CredentialCenterContent({
  activeAuditCredentialId,
  activeFormKey,
  activeInitialState,
  credentials,
  editableCredential,
  feedback,
  isFormPending,
  mode,
  overrideInfoByCredentialId,
  pendingAction,
  shouldShowEditLoadingState,
  onAction,
  onResetEditor,
  onSelectCredential,
  onSelectCredentialForEdit,
  onSubmitCreate,
  onSubmitUpdate,
}: Readonly<CredentialCenterContentProps>) {
  if (credentials && credentials.length > 0) {
    return (
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <CredentialCenterList
          activeCredentialId={mode === "audit" ? activeAuditCredentialId : editableCredential?.id ?? null}
          credentials={credentials}
          isPending={isFormPending}
          mode={mode}
          overrideInfoByCredentialId={overrideInfoByCredentialId}
          pendingAction={pendingAction}
          onAction={onAction}
          onSelectCredential={onSelectCredential ? (credentialId) => onSelectCredential(credentialId) : undefined}
          onSelectCredentialForEdit={
            onSelectCredentialForEdit ? (credentialId) => onSelectCredentialForEdit(credentialId) : undefined
          }
        />
        {mode === "audit" ? (
          <CredentialAuditPanel credentialId={activeAuditCredentialId} />
        ) : shouldShowEditLoadingState ? (
          <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载凭证详情...</div>
        ) : (
          <CredentialCenterForm
            key={activeFormKey}
            feedback={feedback}
            initialState={activeInitialState}
            mode={editableCredential ? "edit" : "create"}
            isPending={isFormPending}
            onReset={editableCredential ? onResetEditor : undefined}
            onSubmit={(formState) => {
              if (editableCredential) {
                onSubmitUpdate(editableCredential, formState);
                return;
              }
              onSubmitCreate(formState);
            }}
          />
        )}
      </div>
    );
  }
  if (mode === "audit") {
    return <EmptyState title="暂无凭证" description="创建凭证后，可以查看其审计记录。" />;
  }
  if (shouldShowEditLoadingState) {
    return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载凭证详情...</div>;
  }
  return (
    <CredentialCenterForm
      key={activeFormKey}
      feedback={feedback}
      initialState={createInitialCredentialForm()}
      mode="create"
      isPending={isFormPending}
      onSubmit={onSubmitCreate}
    />
  );
}
