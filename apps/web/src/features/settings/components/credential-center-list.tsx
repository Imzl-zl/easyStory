"use client";

import { useState } from "react";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  isPendingCredentialAction,
  resolveCredentialActionButtonLabel,
  type PendingCredentialAction,
} from "@/features/settings/components/credential-center-action-support";
import { CredentialDeleteConfirmDialog } from "@/features/settings/components/credential-delete-confirm-dialog";
import type { CredentialOverrideInfo } from "@/features/settings/components/credential-center-override-support";
import {
  formatAuditTime,
  formatCredentialBaseUrl,
  getApiDialectLabel,
  type CredentialCenterMode,
} from "@/features/settings/components/credential-center-support";
import type { CredentialView } from "@/lib/api/types";

type CredentialCenterListProps = {
  credentials: CredentialView[];
  activeCredentialId: string | null;
  mode: CredentialCenterMode;
  isPending: boolean;
  overrideInfoByCredentialId?: Record<string, CredentialOverrideInfo>;
  pendingAction: PendingCredentialAction | null;
  onAction: (type: PendingCredentialAction["type"], credentialId: string) => void;
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
  onSelectCredential,
  onSelectCredentialForEdit,
}: CredentialCenterListProps) {
  const [pendingDeleteCredential, setPendingDeleteCredential] = useState<CredentialView | null>(null);
  const isListMode = mode === "list";

  return (
    <>
      <div className="space-y-3">
        {credentials.map((credential) => {
          const overrideInfo = overrideInfoByCredentialId[credential.id];
          const toggleActionType = credential.is_active ? "disable" : "enable";
          const isVerifyPending = isPendingCredentialAction(pendingAction, "verify", credential.id);
          const isTogglePending = isPendingCredentialAction(pendingAction, toggleActionType, credential.id);
          const isDeletePending = isPendingCredentialAction(pendingAction, "delete", credential.id);
          return (
            <article
              key={credential.id}
              className="panel-muted flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between"
              data-active={credential.id === activeCredentialId}
            >
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-medium">{credential.display_name}</h3>
                  <StatusBadge
                    status={credential.is_active ? "active" : "archived"}
                    label={credential.is_active ? "启用中" : "已停用"}
                  />
                  {overrideInfo ? (
                    <span
                      className="rounded-full border border-[rgba(31,27,22,0.18)] bg-[rgba(31,27,22,0.06)] px-3 py-1 text-xs text-[var(--accent-ink)]"
                      title={`当前项目已配置项目级凭证「${overrideInfo.projectCredentialDisplayName}」，运行时会优先使用项目级凭证。`}
                    >
                      已被项目级重载
                    </span>
                  ) : null}
                  {mode === "audit" ? (
                    <button
                      className="ink-tab"
                      data-active={credential.id === activeCredentialId}
                      disabled={isPending}
                      onClick={() => onSelectCredential?.(credential.id)}
                      type="button"
                    >
                      审计
                    </button>
                  ) : null}
                </div>
                <p className="text-sm text-[var(--text-secondary)]">
                  渠道键：{credential.provider} · 接口：{getApiDialectLabel(credential.api_dialect)}
                </p>
                <p className="text-sm text-[var(--text-secondary)]">
                  默认模型：{credential.default_model ?? "未配置"} · Key：{credential.masked_key}
                </p>
                <p className="text-xs text-[var(--text-secondary)]">
                  Base URL：{formatCredentialBaseUrl(credential.api_dialect, credential.base_url)} · 最近验证：
                  {credential.last_verified_at ? formatAuditTime(credential.last_verified_at) : "未验证"}
                </p>
                {overrideInfo ? (
                  <p className="text-xs text-[var(--accent-ink)]">
                    当前项目已配置同 provider 的项目级凭证「{overrideInfo.projectCredentialDisplayName}」，运行时将优先使用项目级凭证。
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                {isListMode ? (
                  <button
                    className="ink-button-secondary"
                    disabled={isPending}
                    onClick={() => onSelectCredentialForEdit?.(credential.id)}
                    type="button"
                  >
                    编辑
                  </button>
                ) : null}
                {isListMode ? (
                  <>
                    <button
                      className="ink-button-secondary"
                      disabled={isPending}
                      onClick={() => onAction("verify", credential.id)}
                      type="button"
                    >
                      {resolveCredentialActionButtonLabel("verify", isVerifyPending)}
                    </button>
                    <button
                      className="ink-button-secondary"
                      disabled={isPending}
                      onClick={() => onAction(toggleActionType, credential.id)}
                      type="button"
                    >
                      {resolveCredentialActionButtonLabel(toggleActionType, isTogglePending)}
                    </button>
                    <button
                      className="ink-button-danger"
                      disabled={isPending}
                      onClick={() => setPendingDeleteCredential(credential)}
                      type="button"
                    >
                      {resolveCredentialActionButtonLabel("delete", isDeletePending)}
                    </button>
                  </>
                ) : null}
              </div>
            </article>
          );
        })}
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
