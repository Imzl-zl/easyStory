"use client";

import { useState } from "react";

import { CredentialDeleteConfirmDialog } from "@/features/settings/components/credential/credential-delete-confirm-dialog";
import { CredentialCenterListItem } from "@/features/settings/components/credential/credential-center-list-item";
import type { PendingCredentialAction } from "@/features/settings/components/credential/credential-center-action-support";
import type { CredentialOverrideInfo } from "@/features/settings/components/credential/credential-center-override-support";
import type { CredentialCenterMode } from "@/features/settings/components/credential/credential-center-support";
import type { CredentialView } from "@/lib/api/types";

type CredentialCenterListProps = {
  credentials: CredentialView[];
  activeCredentialId: string | null;
  mode: CredentialCenterMode;
  isPending: boolean;
  overrideInfoByCredentialId?: Record<string, CredentialOverrideInfo>;
  pendingAction: PendingCredentialAction | null;
  onAction: (type: PendingCredentialAction["type"], credentialId: string) => void;
  onStartCreate?: () => void;
  onSelectCredential?: (credentialId: string) => void;
  onSelectCredentialForEdit?: (credentialId: string) => void;
};

export function CredentialCenterList({
  credentials,
  activeCredentialId,
  mode,
  isPending,
  overrideInfoByCredentialId = {},
  pendingAction,
  onAction,
  onStartCreate,
  onSelectCredential,
  onSelectCredentialForEdit,
}: CredentialCenterListProps) {
  const [pendingDeleteCredential, setPendingDeleteCredential] = useState<CredentialView | null>(null);

  return (
    <>
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3.5">
          <div className="space-y-1.5">
            <h3 className="font-serif text-lg font-semibold text-text-primary">已有连接</h3>
            <p className="max-w-2xl text-sm leading-6 text-text-secondary">
              把基础连通性、流式链路和工具续接拆开看，当前这张列表会直接反映每条连接的真实验证层级。
            </p>
          </div>
          {mode === "list" && onStartCreate ? (
            <button
              className="ink-button-secondary h-9 px-4 text-[13px]"
              disabled={isPending}
              onClick={onStartCreate}
              type="button"
            >
              添加新连接
            </button>
          ) : null}
        </div>
        <div className="space-y-3">
          {credentials.map((credential) => (
            <CredentialCenterListItem
              key={credential.id}
              credential={credential}
              isActive={credential.id === activeCredentialId}
              isPending={isPending}
              mode={mode}
              overrideInfo={overrideInfoByCredentialId[credential.id]}
              pendingAction={pendingAction}
              onAction={onAction}
              onOpenDelete={setPendingDeleteCredential}
              onSelectCredential={onSelectCredential}
              onSelectCredentialForEdit={onSelectCredentialForEdit}
            />
          ))}
        </div>
      </div>
      {pendingDeleteCredential ? (
        <CredentialDeleteConfirmDialog
          credential={pendingDeleteCredential}
          onClose={() => setPendingDeleteCredential(null)}
          onConfirm={() => {
            onAction("delete", pendingDeleteCredential.id);
            setPendingDeleteCredential(null);
          }}
        />
      ) : null}
    </>
  );
}
