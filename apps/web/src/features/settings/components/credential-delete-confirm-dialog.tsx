"use client";

import { DialogShell } from "@/components/ui/dialog-shell";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildCredentialDeleteImpactItems,
  getCredentialScopeLabel,
} from "@/features/settings/components/credential-delete-confirm-support";
import type { CredentialView } from "@/lib/api/types";

type CredentialDeleteConfirmDialogProps = {
  credential: CredentialView;
  onClose: () => void;
  onConfirm: () => void;
};

export function CredentialDeleteConfirmDialog({
  credential,
  onClose,
  onConfirm,
}: Readonly<CredentialDeleteConfirmDialogProps>) {
  const items = buildCredentialDeleteImpactItems(credential);
  const scopeLabel = getCredentialScopeLabel(credential);

  return (
    <DialogShell
      title={`确认删除${scopeLabel}`}
      description="删除后无法恢复，请确认影响范围。"
      onClose={onClose}
    >
      <div className="grid gap-4 xl:grid-cols-[0.96fr_1.04fr]">
        <section className="panel-muted space-y-4 p-5">
          <div className="space-y-3">
            <StatusBadge status="failed" label="删除确认" />
            <div className="rounded-2xl border border-[rgba(178,65,46,0.16)] bg-[rgba(178,65,46,0.08)] px-4 py-4 text-sm leading-6 text-[var(--accent-danger)]">
              删除后不会自动补一条替代连接。请确认移除后，相关模型还能按你的预期继续使用。
            </div>
          </div>
          <div className="space-y-3 rounded-[18px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.68)] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">{scopeLabel}</p>
            <h3 className="font-serif text-xl font-semibold text-[var(--text-primary)]">
              {credential.display_name}
            </h3>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              连接标识：{credential.provider} · 接口类型：{credential.api_dialect}
            </p>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              当前状态：{credential.is_active ? "启用中" : "已停用"} · 密钥尾号：{credential.masked_key}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="ink-button-danger" onClick={onConfirm} type="button">
              确认删除
            </button>
            <button className="ink-button-secondary" onClick={onClose} type="button">
              先保留
            </button>
          </div>
        </section>
        <section className="panel-muted space-y-4 p-5">
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">删除影响</h3>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              这里只展示当前已经确认的影响，不会替你假设额外回退规则。
            </p>
          </div>
          <div className="space-y-3">
            {items.map((item) => (
              <article
                className="rounded-[18px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.68)] px-4 py-3"
                key={item}
              >
                <p className="text-sm leading-6 text-[var(--text-secondary)]">{item}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </DialogShell>
  );
}
