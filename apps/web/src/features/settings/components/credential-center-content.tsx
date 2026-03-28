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
  onDirtyChange?: (isDirty: boolean) => void;
  overrideInfoByCredentialId: Record<string, CredentialOverrideInfo>;
  pendingAction: PendingCredentialAction | null;
  shouldShowEditLoadingState: boolean;
  onAction: (type: PendingCredentialAction["type"], credentialId: string) => void;
  onResetEditor?: () => void;
  onStartCreate?: () => void;
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
  onDirtyChange,
  overrideInfoByCredentialId,
  pendingAction,
  shouldShowEditLoadingState,
  onAction,
  onResetEditor,
  onStartCreate,
  onSelectCredential,
  onSelectCredentialForEdit,
  onSubmitCreate,
  onSubmitUpdate,
}: Readonly<CredentialCenterContentProps>) {
  if (credentials && credentials.length > 0) {
    return (
      <div className="space-y-4">
        {feedback?.message ? <FeedbackBanner feedback={feedback} /> : null}
        <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <CredentialCenterList
            activeCredentialId={mode === "audit" ? activeAuditCredentialId : editableCredential?.id ?? null}
            credentials={credentials}
            isPending={isFormPending}
            mode={mode}
            overrideInfoByCredentialId={overrideInfoByCredentialId}
            pendingAction={pendingAction}
            onAction={onAction}
            onStartCreate={onStartCreate}
            onSelectCredential={onSelectCredential ? (credentialId) => onSelectCredential(credentialId) : undefined}
            onSelectCredentialForEdit={
              onSelectCredentialForEdit ? (credentialId) => onSelectCredentialForEdit(credentialId) : undefined
            }
          />
          {mode === "audit" ? (
            <CredentialAuditPanel credentialId={activeAuditCredentialId} />
          ) : shouldShowEditLoadingState ? (
            <div className="panel-muted px-4 py-4 text-[13px] leading-5 text-[var(--text-secondary)]">正在加载连接详情…</div>
          ) : (
            <CredentialCenterForm
              key={activeFormKey}
              feedback={null}
              initialState={activeInitialState}
              layout="split"
              mode={editableCredential ? "edit" : "create"}
              isPending={isFormPending}
              onDirtyChange={onDirtyChange}
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
      </div>
    );
  }
  if (mode === "audit") {
    return <EmptyState title="暂无模型连接" description="创建模型连接后可查看操作记录。" />;
  }
  if (shouldShowEditLoadingState) {
    return <div className="panel-muted px-4 py-4 text-[13px] leading-5 text-[var(--text-secondary)]">正在加载连接详情…</div>;
  }
  return (
    <CredentialCenterForm
      key={activeFormKey}
      feedback={feedback}
      initialState={createInitialCredentialForm()}
      layout="full"
      mode="create"
      isPending={isFormPending}
      onDirtyChange={onDirtyChange}
      onSubmit={onSubmitCreate}
    />
  );
}

function FeedbackBanner({ feedback }: { feedback: NonNullable<CredentialCenterFeedback> }) {
  const className =
    feedback.tone === "danger"
      ? "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
      : "bg-[rgba(58,124,165,0.1)] text-[var(--accent-info)]";

  return <div className={`rounded-xl px-3.5 py-2.5 text-[13px] leading-5 ${className}`}>{feedback.message}</div>;
}
