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
      description="这是删除式操作。请先确认移除后，对当前作用域和运行时解析会产生什么影响。"
      onClose={onClose}
    >
      <div className="grid gap-4 xl:grid-cols-[0.96fr_1.04fr]">
        <section className="panel-muted space-y-4 p-5">
          <div className="space-y-3">
            <StatusBadge status="failed" label="删除确认" />
            <div className="rounded-2xl border border-[rgba(178,65,46,0.16)] bg-[rgba(178,65,46,0.08)] px-4 py-4 text-sm leading-6 text-[var(--accent-danger)]">
              删除不会做静默兜底。请确认这条凭证移除后，相关 provider 的解析结果仍符合你的预期。
            </div>
          </div>
          <div className="space-y-3 rounded-[18px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.68)] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">{scopeLabel}</p>
            <h3 className="font-serif text-xl font-semibold text-[var(--text-primary)]">
              {credential.display_name}
            </h3>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              渠道键：{credential.provider} · 接口：{credential.api_dialect}
            </p>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              当前状态：{credential.is_active ? "启用中" : "已停用"} · Key：{credential.masked_key}
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
              这里只展示当前代码与文档已确认的解析规则，不替你假设未来回退结果。
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
