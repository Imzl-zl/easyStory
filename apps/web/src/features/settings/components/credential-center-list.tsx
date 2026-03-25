"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import {
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
  onAction: (type: "verify" | "enable" | "disable" | "delete", credentialId: string) => void;
  onSelectCredential?: (credentialId: string) => void;
};

export function CredentialCenterList({
  credentials,
  activeCredentialId,
  mode,
  isPending,
  onAction,
  onSelectCredential,
}: CredentialCenterListProps) {
  return (
    <div className="space-y-3">
      {credentials.map((credential) => (
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
              {mode === "audit" ? (
                <button
                  className="ink-tab"
                  data-active={credential.id === activeCredentialId}
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
              {credential.last_verified_at ?? "未验证"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="ink-button-secondary"
              disabled={isPending}
              onClick={() => onAction("verify", credential.id)}
              type="button"
            >
              验证
            </button>
            <button
              className="ink-button-secondary"
              disabled={isPending}
              onClick={() => onAction(credential.is_active ? "disable" : "enable", credential.id)}
              type="button"
            >
              {credential.is_active ? "停用" : "启用"}
            </button>
            <button
              className="ink-button-danger"
              disabled={isPending}
              onClick={() => onAction("delete", credential.id)}
              type="button"
            >
              删除
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
