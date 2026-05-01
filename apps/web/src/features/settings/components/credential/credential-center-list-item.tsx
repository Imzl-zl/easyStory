"use client";

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

  const isVerifyStreamConnectionPending = isPendingCredentialAction(pendingAction, "verify_stream_connection", credential.id);
  const isVerifyBufferedConnectionPending = isPendingCredentialAction(pendingAction, "verify_buffered_connection", credential.id);
  const isVerifyStreamToolsPending = isPendingCredentialAction(pendingAction, "verify_stream_tools", credential.id);
  const isVerifyBufferedToolsPending = isPendingCredentialAction(pendingAction, "verify_buffered_tools", credential.id);
  const isTogglePending = isPendingCredentialAction(pendingAction, toggleActionType, credential.id);
  const isDeletePending = isPendingCredentialAction(pendingAction, "delete", credential.id);

  return (
    <article
      className="rounded-lg transition-all duration-150"
      style={{
        background: isActive ? "var(--bg-muted)" : "var(--bg-canvas)",
        border: isActive ? "1px solid var(--line-medium)" : "1px solid transparent",
        boxShadow: isActive ? "0 0 0 1px var(--line-medium)" : "none",
      }}
    >
      {/* Header Row - Always visible */}
      <div className="flex items-center justify-between gap-4 px-4 py-3.5">
        <div className="flex items-center gap-3 min-w-0">
          {/* Status Dot */}
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{
              background: credential.is_active ? "var(--accent-success)" : "var(--text-tertiary)",
              boxShadow: credential.is_active ? "0 0 8px var(--accent-success-soft)" : "none",
            }}
          />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-[13px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                {credential.display_name}
              </h3>
              {overrideInfo ? (
                <span
                  className="flex-shrink-0 text-[9px] font-medium px-1 py-0.5 rounded"
                  style={{ background: "var(--accent-primary-soft)", color: "var(--accent-primary)" }}
                  title={`当前项目已配置项目级模型连接「${overrideInfo.projectCredentialDisplayName}」`}
                >
                  覆盖
                </span>
              ) : null}
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{credential.provider}</span>
              <span style={{ color: "var(--text-tertiary)" }}>·</span>
              <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{getApiDialectLabel(credential.api_dialect)}</span>
              <span style={{ color: "var(--text-tertiary)" }}>·</span>
              <span className="text-[10px] truncate" style={{ color: "var(--text-tertiary)" }}>{credential.default_model ?? "无默认模型"}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Capability Dots */}
          <div className="flex items-center gap-1 mr-2">
            <CapabilityDot capability={streamCapability} />
            <CapabilityDot capability={bufferedCapability} />
          </div>

          {mode === "audit" ? (
            <button
              className="px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors"
              data-active={isActive}
              disabled={isPending}
              onClick={() => onSelectCredential?.(credential.id)}
              style={{
                background: isActive ? "var(--bg-elevated)" : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-tertiary)",
                border: "1px solid var(--line-medium)",
              }}
              type="button"
            >
              审计
            </button>
          ) : (
            <button
              className="px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors"
              disabled={isPending}
              onClick={() => onSelectCredentialForEdit?.(credential.id)}
              style={{
                background: isActive ? "var(--bg-elevated)" : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-tertiary)",
                border: "1px solid var(--line-medium)",
              }}
              type="button"
            >
              {isActive ? "编辑中" : "编辑"}
            </button>
          )}
        </div>
      </div>

      {/* Expanded Details */}
      {isActive && (
        <div className="px-4 pb-4" style={{ borderTop: "1px solid var(--line-soft)" }}>
          {/* Info Grid */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 py-3">
            <InfoRow label="密钥" value={`尾号 ${credential.masked_key}`} />
            <InfoRow label="地址" value={formatCredentialBaseUrl(credential.api_dialect, credential.base_url)} />
            <InfoRow label="Token" value={formatCredentialTokenSummary(credential)} />
            <InfoRow label="验证" value={credential.last_verified_at ? formatAuditTime(credential.last_verified_at) : "从未验证"} />
          </div>

          {/* Capability Details */}
          <div className="space-y-1.5 py-2" style={{ borderTop: "1px solid var(--line-soft)" }}>
            <CapabilityRow capability={streamCapability} />
            <CapabilityRow capability={bufferedCapability} />
          </div>

          {/* Actions */}
          {mode === "list" && (
            <div className="flex items-center justify-between gap-3 pt-3" style={{ borderTop: "1px solid var(--line-soft)" }}>
              <div className="flex flex-wrap gap-1.5">
                <ActionButton label={resolveCredentialActionButtonLabel("verify_stream_connection", isVerifyStreamConnectionPending)} onClick={() => onAction("verify_stream_connection", credential.id)} isPending={isVerifyStreamConnectionPending} />
                <ActionButton label={resolveCredentialActionButtonLabel("verify_buffered_connection", isVerifyBufferedConnectionPending)} onClick={() => onAction("verify_buffered_connection", credential.id)} isPending={isVerifyBufferedConnectionPending} />
                <ActionButton label={resolveCredentialActionButtonLabel("verify_stream_tools", isVerifyStreamToolsPending)} onClick={() => onAction("verify_stream_tools", credential.id)} isPending={isVerifyStreamToolsPending} />
                <ActionButton label={resolveCredentialActionButtonLabel("verify_buffered_tools", isVerifyBufferedToolsPending)} onClick={() => onAction("verify_buffered_tools", credential.id)} isPending={isVerifyBufferedToolsPending} />
              </div>
              <div className="flex gap-1.5">
                <ActionButton label={resolveCredentialActionButtonLabel(toggleActionType, isTogglePending)} onClick={() => onAction(toggleActionType, credential.id)} isPending={isTogglePending} />
                <button
                  className="h-6 px-2 rounded text-[10px] font-medium transition-colors"
                  disabled={isPending}
                  onClick={() => onOpenDelete(credential)}
                  style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
                  type="button"
                >
                  {resolveCredentialActionButtonLabel("delete", isDeletePending)}
                </button>
              </div>
            </div>
          )}

          {overrideInfo && (
            <p className="mt-3 text-[10px]" style={{ color: "var(--accent-primary)" }}>
              当前项目已配置同标识的项目级连接「{overrideInfo.projectCredentialDisplayName}」，运行时会优先使用。
            </p>
          )}
        </div>
      )}
    </article>
  );
}

function CapabilityDot({ capability }: { capability: { tone: string; summary: string } }) {
  const colorMap: Record<string, string> = {
    completed: "var(--accent-success)",
    ready: "var(--accent-primary)",
    warning: "var(--accent-warning)",
    draft: "var(--text-tertiary)",
  };
  return (
    <span
      className="w-1.5 h-1.5 rounded-full"
      style={{
        background: colorMap[capability.tone] || "var(--text-tertiary)",
        boxShadow: capability.tone === "completed" ? "0 0 4px var(--accent-success-soft)" : "none",
      }}
      title={capability.summary}
    />
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] flex-shrink-0" style={{ color: "var(--text-tertiary)", width: "32px" }}>{label}</span>
      <span className="text-[11px] truncate" style={{ color: "var(--text-secondary)" }}>{value}</span>
    </div>
  );
}

function CapabilityRow({ capability }: { capability: { title: string; summary: string; detail: string; tone: string; lastVerifiedAt?: string | null } }) {
  const colorMap: Record<string, { bg: string; text: string }> = {
    completed: { bg: "var(--accent-success-soft)", text: "var(--accent-success)" },
    ready: { bg: "var(--accent-primary-soft)", text: "var(--accent-primary)" },
    warning: { bg: "var(--accent-warning-soft)", text: "var(--accent-warning)" },
    draft: { bg: "var(--bg-surface)", text: "var(--text-tertiary)" },
  };
  const colors = colorMap[capability.tone] || colorMap.draft;

  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-[10px] flex-shrink-0" style={{ color: "var(--text-tertiary)", width: "40px" }}>{capability.title}</span>
        <span className="text-[10px] font-medium px-1 py-0.5 rounded flex-shrink-0" style={{ background: colors.bg, color: colors.text }}>
          {capability.summary}
        </span>
        <span className="text-[10px] truncate" style={{ color: "var(--text-tertiary)" }}>{capability.detail}</span>
      </div>
      {capability.lastVerifiedAt && (
        <span className="text-[9px] flex-shrink-0" style={{ color: "var(--text-tertiary)" }}>{formatAuditTime(capability.lastVerifiedAt)}</span>
      )}
    </div>
  );
}

function ActionButton({ label, onClick, isPending }: { label: string; onClick: () => void; isPending: boolean }) {
  return (
    <button
      className="h-6 px-2 rounded text-[10px] font-medium transition-colors"
      disabled={isPending}
      onClick={onClick}
      style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
      type="button"
    >
      {label}
    </button>
  );
}
