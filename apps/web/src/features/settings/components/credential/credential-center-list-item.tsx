"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildCredentialTransportCapabilityItem,
  formatAuditTime,
  formatCredentialTokenSummary,
} from "@/features/settings/components/credential/credential-center-display-support";
import {
  isPendingCredentialAction,
  resolveCredentialActionButtonLabel,
  type PendingCredentialAction,
} from "@/features/settings/components/credential/credential-center-action-support";
import type { CredentialOverrideInfo } from "@/features/settings/components/credential/credential-center-override-support";
import {
  formatCredentialBaseUrl,
  getApiDialectLabel,
  type CredentialCenterMode,
} from "@/features/settings/components/credential/credential-center-support";
import type { CredentialView } from "@/lib/api/types";

type CredentialCenterListItemProps = {
  credential: CredentialView;
  isActive: boolean;
  isPending: boolean;
  mode: CredentialCenterMode;
  overrideInfo?: CredentialOverrideInfo;
  pendingAction: PendingCredentialAction | null;
  onAction: (type: PendingCredentialAction["type"], credentialId: string) => void;
  onOpenDelete: (credential: CredentialView) => void;
  onSelectCredential?: (credentialId: string) => void;
  onSelectCredentialForEdit?: (credentialId: string) => void;
};

export function CredentialCenterListItem({
  credential,
  isActive,
  isPending,
  mode,
  overrideInfo,
  pendingAction,
  onAction,
  onOpenDelete,
  onSelectCredential,
  onSelectCredentialForEdit,
}: CredentialCenterListItemProps) {
  const streamCapability = buildCredentialTransportCapabilityItem(credential, "stream");
  const bufferedCapability = buildCredentialTransportCapabilityItem(credential, "buffered");
  const toggleActionType = credential.is_active ? "disable" : "enable";
  const isVerifyStreamConnectionPending = isPendingCredentialAction(
    pendingAction,
    "verify_stream_connection",
    credential.id,
  );
  const isVerifyBufferedConnectionPending = isPendingCredentialAction(
    pendingAction,
    "verify_buffered_connection",
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
      className="panel-muted overflow-hidden p-0"
      data-active={isActive}
    >
      <div className="flex flex-col">
        <header className="flex flex-wrap items-start justify-between gap-4 px-5 py-4">
          <div className="min-w-0 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-text-primary">{credential.display_name}</h3>
              <StatusBadge
                status={credential.is_active ? "active" : "archived"}
                label={credential.is_active ? "启用中" : "已停用"}
              />
              {overrideInfo ? (
                <span
                  className="inline-flex rounded-lg border border-line-strong bg-surface-hover px-2.5 py-1 text-[11px] font-medium text-accent-primary"
                  title={`当前项目已配置项目级模型连接「${overrideInfo.projectCredentialDisplayName}」，运行时会优先使用项目级连接。`}
                >
                  项目级覆盖
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2 text-[12px] leading-5 text-text-secondary">
              <span className="inline-flex rounded-lg border border-line-soft bg-surface px-2.5 py-1">
                {credential.provider}
              </span>
              <span className="inline-flex rounded-lg border border-line-soft bg-surface px-2.5 py-1">
                {getApiDialectLabel(credential.api_dialect)}
              </span>
              <span className="inline-flex rounded-lg border border-line-soft bg-surface px-2.5 py-1">
                默认模型：{credential.default_model ?? "未配置"}
              </span>
              <span className="inline-flex rounded-lg border border-line-soft bg-surface px-2.5 py-1">
                密钥尾号：{credential.masked_key}
              </span>
            </div>
          </div>
          {mode === "audit" ? (
            <button
              className="ink-tab"
              data-active={isActive}
              disabled={isPending}
              onClick={() => onSelectCredential?.(credential.id)}
              type="button"
            >
              审计
            </button>
          ) : (
            <button
              className="ink-button-secondary h-9 px-4 text-[13px]"
              disabled={isPending}
              onClick={() => onSelectCredentialForEdit?.(credential.id)}
              type="button"
            >
              编辑
            </button>
          )}
        </header>

        <div className="border-t border-line-soft px-5 py-4">
          <div className="grid gap-3 text-[13px] leading-6 text-text-secondary sm:grid-cols-2">
            <p>{formatCredentialTokenSummary(credential)}</p>
            <p>服务地址：{formatCredentialBaseUrl(credential.api_dialect, credential.base_url)}</p>
            {credential.last_verified_at ? (
              <p>历史基础验证：{formatAuditTime(credential.last_verified_at)}</p>
            ) : (
              <p>当前以两条链路状态作为页面真值。</p>
            )}
            {mode === "list" ? (
              <p>下面的按钮会直接更新流式链路和非流链路的验证状态。</p>
            ) : (
              <p>审计模式只查看记录，不改动任何验证状态。</p>
            )}
          </div>
        </div>

        <div className="border-t border-line-soft px-5 py-4">
          <div className="space-y-3">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-text-secondary">链路验证</p>
            {[streamCapability, bufferedCapability].map((item) => (
              <section
                key={item.title}
                className="flex flex-wrap items-start justify-between gap-3 border-t border-line-soft pt-3 first:border-t-0 first:pt-0"
              >
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">{item.title}</span>
                    <StatusBadge status={item.tone} label={item.summary} />
                  </div>
                  <p className="text-[12px] leading-5 text-text-secondary">{item.detail}</p>
                </div>
                <p className="text-[12px] leading-5 text-text-secondary">
                  {item.lastVerifiedAt ? `最近验证：${formatAuditTime(item.lastVerifiedAt)}` : "未验证"}
                </p>
              </section>
            ))}
          </div>
          {overrideInfo ? (
            <p className="mt-3 text-[12px] leading-5 text-accent-primary">
              当前项目已配置同连接标识的项目级模型连接“{overrideInfo.projectCredentialDisplayName}”，运行时会优先使用项目级连接。
            </p>
          ) : null}
        </div>

        {mode === "list" ? (
          <div className="border-t border-line-soft px-5 py-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                <button
                  className="ink-button-secondary h-9 px-3.5 text-[13px]"
                  disabled={isPending}
                  onClick={() => onAction("verify_stream_connection", credential.id)}
                  type="button"
                >
                  {resolveCredentialActionButtonLabel("verify_stream_connection", isVerifyStreamConnectionPending)}
                </button>
                <button
                  className="ink-button-secondary h-9 px-3.5 text-[13px]"
                  disabled={isPending}
                  onClick={() => onAction("verify_buffered_connection", credential.id)}
                  type="button"
                >
                  {resolveCredentialActionButtonLabel("verify_buffered_connection", isVerifyBufferedConnectionPending)}
                </button>
                <button
                  className="ink-button-secondary h-9 px-3.5 text-[13px]"
                  disabled={isPending}
                  onClick={() => onAction("verify_stream_tools", credential.id)}
                  type="button"
                >
                  {resolveCredentialActionButtonLabel("verify_stream_tools", isVerifyStreamToolsPending)}
                </button>
                <button
                  className="ink-button-secondary h-9 px-3.5 text-[13px]"
                  disabled={isPending}
                  onClick={() => onAction("verify_buffered_tools", credential.id)}
                  type="button"
                >
                  {resolveCredentialActionButtonLabel("verify_buffered_tools", isVerifyBufferedToolsPending)}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="ink-button-secondary h-9 px-3.5 text-[13px]"
                  disabled={isPending}
                  onClick={() => onAction(toggleActionType, credential.id)}
                  type="button"
                >
                  {resolveCredentialActionButtonLabel(toggleActionType, isTogglePending)}
                </button>
                <button
                  className="ink-button-danger h-9 px-3.5 text-[13px]"
                  disabled={isPending}
                  onClick={() => onOpenDelete(credential)}
                  type="button"
                >
                  {resolveCredentialActionButtonLabel("delete", isDeletePending)}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </article>
  );
}
