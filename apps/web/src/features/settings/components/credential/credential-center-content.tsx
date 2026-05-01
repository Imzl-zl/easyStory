"use client";

import { EmptyState } from "@/components/ui/empty-state";
import type { PendingCredentialAction } from "@/features/settings/components/credential/credential-center-action-support";
import { CredentialCenterForm } from "@/features/settings/components/credential/credential-center-form";
import { CredentialCenterList } from "@/features/settings/components/credential/credential-center-list";
import type { CredentialOverrideInfo } from "@/features/settings/components/credential/credential-center-override-support";
import { CredentialAuditPanel } from "@/features/settings/components/credential/credential-audit-panel";
import type {
  CredentialCenterMode,
  CredentialFormState,
} from "@/features/settings/components/credential/credential-center-support";
import { createInitialCredentialForm } from "@/features/settings/components/credential/credential-center-support";
import type { CredentialView } from "@/lib/api/types";

type CredentialCenterContentProps = {
  activeAuditCredentialId: string | null;
  activeFormKey: string;
  activeInitialState: CredentialFormState;
  credentials: CredentialView[] | undefined;
  editableCredential: CredentialView | null;
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
  const listItems = credentials
    ? credentials.map((c) => ({
        id: c.id,
        name: c.display_name,
        provider: c.provider,
        dialect: (c as any).dialect ?? c.provider,
        model: c.default_model,
        isActive: c.is_active,
        isSelected:
          mode === "audit"
            ? c.id === activeAuditCredentialId
            : c.id === (editableCredential?.id ?? null),
        overrideInfo: overrideInfoByCredentialId[c.id],
        streamStatus: resolveStreamStatus(c),
        bufferedStatus: resolveBufferedStatus(c),
      }))
    : [];

  if (credentials && credentials.length > 0) {
    return (
      <div className="flex gap-5">
        {/* List Panel */}
        <div className="flex-1 min-w-0">
          <CredentialCenterList
            items={listItems}
            isPending={isFormPending}
            onAction={onAction}
            onEdit={(id) => onSelectCredentialForEdit?.(id)}
            onSelect={(id) => onSelectCredential?.(id)}
            pendingAction={pendingAction}
          />
        </div>

        {/* Side Panel */}
        <div className="w-[380px] flex-shrink-0">
          {mode === "audit" ? (
            <CredentialAuditPanel credentialId={activeAuditCredentialId} />
          ) : shouldShowEditLoadingState ? (
            <div className="rounded-lg px-4 py-5 text-[13px]" style={{ background: "var(--bg-canvas)", color: "var(--text-tertiary)", border: "1px solid var(--line-soft)" }}>
              正在加载连接详情…
            </div>
          ) : (
            <CredentialCenterForm
              key={activeFormKey}
              credential={editableCredential}
              feedback={null}
              initialState={activeInitialState}
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
    return (
      <div className="rounded-lg px-6 py-8 text-center" style={{ background: "var(--bg-canvas)", border: "1px dashed var(--line-medium)" }}>
        <p className="text-[13px] font-medium" style={{ color: "var(--text-secondary)" }}>暂无模型连接</p>
        <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>创建模型连接后可查看操作记录。</p>
      </div>
    );
  }

  if (shouldShowEditLoadingState) {
    return (
      <div className="rounded-lg px-4 py-5 text-[13px]" style={{ background: "var(--bg-canvas)", color: "var(--text-tertiary)", border: "1px solid var(--line-soft)" }}>
        正在加载连接详情…
      </div>
    );
  }

  return (
    <div className="flex gap-5">
      <div className="flex-1">
        <div className="rounded-lg px-6 py-8 text-center" style={{ background: "var(--bg-canvas)", border: "1px dashed var(--line-medium)" }}>
          <p className="text-[13px] font-medium" style={{ color: "var(--text-secondary)" }}>还没有模型连接</p>
          <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>在右侧表单中添加你的第一个连接</p>
        </div>
      </div>
      <div className="w-[380px] flex-shrink-0">
        <CredentialCenterForm
          key={activeFormKey}
          credential={null}
          feedback={null}
          initialState={createInitialCredentialForm()}
          mode="create"
          isPending={isFormPending}
          onDirtyChange={onDirtyChange}
          onSubmit={onSubmitCreate}
        />
      </div>
    </div>
  );
}

function resolveStreamStatus(c: CredentialView): "ok" | "warning" | "error" | "unknown" {
  const s = (c as any).capabilities?.stream;
  if (!s) return "unknown";
  if (s.connection_verified && s.tools_verified) return "ok";
  if (s.connection_verified || s.tools_verified) return "warning";
  return "error";
}

function resolveBufferedStatus(c: CredentialView): "ok" | "warning" | "error" | "unknown" {
  const s = (c as any).capabilities?.buffered;
  if (!s) return "unknown";
  if (s.connection_verified && s.tools_verified) return "ok";
  if (s.connection_verified || s.tools_verified) return "warning";
  return "error";
}
