"use client";

import { useState } from "react";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  formatAuditTime,
  formatCredentialToolCapabilitySummary,
  formatCredentialTokenSummary,
} from "@/features/settings/components/credential/credential-center-display-support";
import {
  isPendingCredentialAction,
  resolveCredentialActionButtonLabel,
  type PendingCredentialAction,
} from "@/features/settings/components/credential/credential-center-action-support";
import { CredentialDeleteConfirmDialog } from "@/features/settings/components/credential/credential-delete-confirm-dialog";
import type { CredentialOverrideInfo } from "@/features/settings/components/credential/credential-center-override-support";
import {
  formatCredentialBaseUrl,
  getApiDialectLabel,
  type CredentialCenterMode,
} from "@/features/settings/components/credential/credential-center-support";
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
  const isListMode = mode === "list";

  return (
    <>
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3.5">
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold text-[var(--text-primary)]">已有连接</h3>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">查看、验证连接与工具兼容性，并管理已有连接。</p>
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
        {credentials.map((credential) => {
          const overrideInfo = overrideInfoByCredentialId[credential.id];
          const toggleActionType = credential.is_active ? "disable" : "enable";
          const isVerifyConnectionPending = isPendingCredentialAction(
            pendingAction,
            "verify_connection",
            credential.id,
          );
          const isVerifyStreamToolsPending = isPendingCredentialAction(
            pendingAction,
            "verify_stream_tools",
            credential.id,
          );
          const isVerifyBufferedToolsPending = isPendingCredentialAction(
            pendingAction,
            "verify_buffered_tools",
            credential.id,
          );
          const isTogglePending = isPendingCredentialAction(pendingAction, toggleActionType, credential.id);
          const isDeletePending = isPendingCredentialAction(pendingAction, "delete", credential.id);
          return (
            <article
              key={credential.id}
              className="panel-muted grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start"
              data-active={credential.id === activeCredentialId}
            >
              <div className="space-y-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-medium">{credential.display_name}</h3>
                  <StatusBadge
                    status={credential.is_active ? "active" : "archived"}
                    label={credential.is_active ? "启用中" : "已停用"}
                  />
                  {overrideInfo ? (
                    <span
                      className="rounded-full border border-[rgba(31,27,22,0.18)] bg-[rgba(31,27,22,0.06)] px-3 py-1 text-xs text-[var(--accent-ink)]"
                      title={`当前项目已配置项目级模型连接「${overrideInfo.projectCredentialDisplayName}」，运行时会优先使用项目级连接。`}
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
                  连接代号：{credential.provider} · 接入方式：{getApiDialectLabel(credential.api_dialect)}
                </p>
                <p className="text-sm text-[var(--text-secondary)]">
                  默认模型：{credential.default_model ?? "未配置"} · 密钥尾号：{credential.masked_key}
                </p>
                <p className="text-sm text-[var(--text-secondary)]">{formatCredentialTokenSummary(credential)}</p>
                <p className="text-sm text-[var(--text-secondary)]">
                  {formatCredentialToolCapabilitySummary(credential, "stream")}
                </p>
                <p className="text-sm text-[var(--text-secondary)]">
                  {formatCredentialToolCapabilitySummary(credential, "buffered")}
                </p>
                <p className="text-xs leading-5 text-[var(--text-secondary)]">
                  服务地址：{formatCredentialBaseUrl(credential.api_dialect, credential.base_url)} · 最近连接验证：
                  {credential.last_verified_at ? formatAuditTime(credential.last_verified_at) : "未验证"}
                </p>
                {overrideInfo ? (
                  <p className="text-xs leading-5 text-[var(--accent-ink)]">
                    当前项目已配置同连接标识的项目级模型连接「{overrideInfo.projectCredentialDisplayName}」，运行时将优先使用项目级连接。
                  </p>
                ) : null}
              </div>
              <div className="flex max-w-full flex-wrap justify-start gap-2.5 lg:max-w-[340px] lg:justify-end">
                {isListMode ? (
                  <button
                    className="ink-button-secondary h-9 min-w-[84px] px-3.5 text-[13px]"
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
                      className="ink-button-secondary h-9 min-w-[84px] px-3.5 text-[13px]"
                      disabled={isPending}
                      onClick={() => onAction("verify_connection", credential.id)}
                      type="button"
                    >
                      {resolveCredentialActionButtonLabel("verify_connection", isVerifyConnectionPending)}
                    </button>
                    <button
                      className="ink-button-secondary h-9 min-w-[84px] px-3.5 text-[13px]"
                      disabled={isPending}
                      onClick={() => onAction("verify_stream_tools", credential.id)}
                      type="button"
                    >
                      {resolveCredentialActionButtonLabel("verify_stream_tools", isVerifyStreamToolsPending)}
                    </button>
                    <button
                      className="ink-button-secondary h-9 min-w-[84px] px-3.5 text-[13px]"
                      disabled={isPending}
                      onClick={() => onAction("verify_buffered_tools", credential.id)}
                      type="button"
                    >
                      {resolveCredentialActionButtonLabel("verify_buffered_tools", isVerifyBufferedToolsPending)}
                    </button>
                    <button
                      className="ink-button-secondary h-9 min-w-[84px] px-3.5 text-[13px]"
                      disabled={isPending}
                      onClick={() => onAction(toggleActionType, credential.id)}
                      type="button"
                    >
                      {resolveCredentialActionButtonLabel(toggleActionType, isTogglePending)}
                    </button>
                    <button
                      className="ink-button-danger h-9 min-w-[84px] px-3.5 text-[13px]"
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
