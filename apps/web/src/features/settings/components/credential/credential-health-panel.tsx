"use client";

import { useMemo } from "react";

import type { PendingCredentialAction } from "@/features/settings/components/credential/credential-center-action-support";
import {
  buildCredentialTransportCapabilityItem,
  formatAuditTime,
  formatCredentialTokenSummary,
} from "@/features/settings/components/credential/credential-center-display-support";
import {
  formatCredentialBaseUrl,
  getApiDialectLabel,
} from "@/features/settings/components/credential/credential-center-support";
import type { CredentialView } from "@/lib/api/types";

type CredentialHealthPanelProps = {
  credential: CredentialView | null;
  credentials: CredentialView[];
  onSelect: (id: string) => void;
  onVerify: (type: PendingCredentialAction["type"], credentialId: string) => void;
  onToggle: (credentialId: string) => void;
  onEdit: (credentialId: string) => void;
  pendingAction: PendingCredentialAction | null;
  isPending: boolean;
};

export function CredentialHealthPanel({
  credential,
  credentials,
  onSelect,
  onVerify,
  onToggle,
  onEdit,
  pendingAction,
  isPending,
}: CredentialHealthPanelProps) {
  if (!credential) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>选择一条连接查看健康状态</p>
        <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>从左侧列表或下方选择</p>

        {/* Quick Select Grid */}
        <div className="grid grid-cols-2 gap-2 mt-6 w-full max-w-md">
          {credentials.map((c) => (
            <button
              key={c.id}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-left"
              style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
              onClick={() => onSelect(c.id)}
            >
              <HealthDot status={getOverallStatus(c)} />
              <span className="text-[12px] truncate" style={{ color: "var(--text-primary)" }}>{c.display_name}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const streamCap = buildCredentialTransportCapabilityItem(credential, "stream");
  const bufferedCap = buildCredentialTransportCapabilityItem(credential, "buffered");
  const overallStatus = getOverallStatus(credential);

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Header Card */}
      <div className="rounded-lg p-5" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: getStatusBg(overallStatus) }}>
              <HealthDot status={overallStatus} size="lg" />
            </div>
            <div>
              <h2 className="text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>{credential.display_name}</h2>
              <p className="text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
                {credential.provider} · {getApiDialectLabel(credential.api_dialect)} · {credential.default_model ?? "无默认模型"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="h-7 px-3 rounded text-[11px] font-medium"
              style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
              onClick={() => onEdit(credential.id)}
              disabled={isPending}
            >
              编辑
            </button>
            <button
              className="h-7 px-3 rounded text-[11px] font-medium"
              style={{
                background: credential.is_active ? "var(--accent-danger-soft)" : "var(--accent-success-soft)",
                color: credential.is_active ? "var(--accent-danger)" : "var(--accent-success)",
              }}
              onClick={() => onToggle(credential.id)}
              disabled={isPending}
            >
              {credential.is_active ? "停用" : "启用"}
            </button>
          </div>
        </div>

        {/* Quick Info */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4" style={{ borderTop: "1px solid var(--line-soft)" }}>
          <InfoItem label="密钥" value={`尾号 ${credential.masked_key}`} />
          <InfoItem label="地址" value={formatCredentialBaseUrl(credential.api_dialect, credential.base_url)} />
          <InfoItem label="Token" value={formatCredentialTokenSummary(credential)} />
        </div>
      </div>

      {/* Linkage Status */}
      <div className="rounded-lg p-5" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
        <h3 className="text-[11px] font-semibold tracking-[0.1em] uppercase mb-4" style={{ color: "var(--accent-primary)" }}>
          链路验证
        </h3>
        <div className="space-y-3">
          <LinkageRow
            title="流式链路"
            capability={streamCap}
            onVerifyConnection={() => onVerify("verify_stream_connection", credential.id)}
            onVerifyTools={() => onVerify("verify_stream_tools", credential.id)}
            isPending={isPending}
          />
          <LinkageRow
            title="非流链路"
            capability={bufferedCap}
            onVerifyConnection={() => onVerify("verify_buffered_connection", credential.id)}
            onVerifyTools={() => onVerify("verify_buffered_tools", credential.id)}
            isPending={isPending}
          />
        </div>
      </div>

      {/* Last Verified */}
      {credential.last_verified_at && (
        <p className="text-[10px] text-center" style={{ color: "var(--text-tertiary)" }}>
          上次验证：{formatAuditTime(credential.last_verified_at)}
        </p>
      )}
    </div>
  );
}

function LinkageRow({
  title,
  capability,
  onVerifyConnection,
  onVerifyTools,
  isPending,
}: {
  title: string;
  capability: { title: string; summary: string; detail: string; tone: string; lastVerifiedAt?: string | null };
  onVerifyConnection: () => void;
  onVerifyTools: () => void;
  isPending: boolean;
}) {
  const isOk = capability.tone === "completed";
  const isWarning = capability.tone === "ready" || capability.tone === "warning";

  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ background: isOk ? "var(--accent-success-soft)" : isWarning ? "var(--accent-warning-soft)" : "var(--accent-danger-soft)" }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={isOk ? "var(--accent-success)" : isWarning ? "var(--accent-warning)" : "var(--accent-danger)"} strokeWidth="2" strokeLinecap="round">
            {isOk ? (
              <>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </>
            ) : (
              <>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" x2="12" y1="8" y2="12" />
                <line x1="12" x2="12.01" y1="16" y2="16" />
              </>
            )}
          </svg>
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>{title}</span>
            <span
              className="text-[10px] px-1.5 py-0.5 rounded font-medium"
              style={{
                background: isOk ? "var(--accent-success-soft)" : isWarning ? "var(--accent-warning-soft)" : "var(--accent-danger-soft)",
                color: isOk ? "var(--accent-success)" : isWarning ? "var(--accent-warning)" : "var(--accent-danger)",
              }}
            >
              {capability.summary}
            </span>
          </div>
          <p className="text-[10px] mt-0.5 truncate" style={{ color: "var(--text-tertiary)" }}>{capability.detail}</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <button
          className="h-6 px-2 rounded text-[10px] font-medium"
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          onClick={onVerifyConnection}
          disabled={isPending}
        >
          验证连接
        </button>
        <button
          className="h-6 px-2 rounded text-[10px] font-medium"
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          onClick={onVerifyTools}
          disabled={isPending}
        >
          验证工具
        </button>
      </div>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{label}</p>
      <p className="text-[12px] mt-0.5 truncate" style={{ color: "var(--text-secondary)" }}>{value}</p>
    </div>
  );
}

function HealthDot({ status, size = "md" }: { status: string; size?: "sm" | "md" | "lg" }) {
  const colors: Record<string, string> = {
    ok: "var(--accent-success)",
    warning: "var(--accent-warning)",
    error: "var(--accent-danger)",
    unknown: "var(--text-tertiary)",
  };
  const color = colors[status] || "var(--text-tertiary)";
  const s = size === "lg" ? "w-3 h-3" : size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2";

  return (
    <span
      className={`${s} rounded-full`}
      style={{
        background: color,
        boxShadow: status !== "unknown" ? `0 0 6px ${color}50` : "none",
        display: "inline-block",
      }}
    />
  );
}

function getStatusBg(status: string): string {
  const map: Record<string, string> = {
    ok: "var(--accent-success-soft)",
    warning: "var(--accent-warning-soft)",
    error: "var(--accent-danger-soft)",
    unknown: "var(--line-soft)",
  };
  return map[status] || "var(--line-soft)";
}

function getOverallStatus(c: CredentialView): "ok" | "warning" | "error" | "unknown" {
  if (!c.is_active) return "unknown";
  const caps = (c as any).capabilities;
  const stream = caps?.stream;
  const buffered = caps?.buffered;
  const streamOk = stream?.connection_verified && stream?.tools_verified;
  const bufferedOk = buffered?.connection_verified && buffered?.tools_verified;
  if (streamOk && bufferedOk) return "ok";
  if (streamOk || bufferedOk) return "warning";
  return "error";
}
