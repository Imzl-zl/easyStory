"use client";

import { useQuery } from "@tanstack/react-query";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { formatAuditTime } from "@/features/settings/components/credential-center-support";
import { getErrorMessage } from "@/lib/api/client";
import { listCredentialAuditLogs } from "@/lib/api/observability";

export function CredentialAuditPanel({ credentialId }: { credentialId: string | null }) {
  const query = useQuery({
    queryKey: ["credential-audit", credentialId],
    queryFn: () => listCredentialAuditLogs(credentialId as string),
    enabled: Boolean(credentialId),
  });

  if (!credentialId) {
    return <EmptyState title="先选一条模型连接" description="选中左侧连接后，就能查看它的操作记录。" />;
  }
  if (query.isLoading) {
    return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载审计日志...</div>;
  }
  if (query.error) {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {getErrorMessage(query.error)}
      </div>
    );
  }
  if ((query.data?.length ?? 0) === 0) {
    return <EmptyState title="暂无审计日志" description="这条模型连接还没有操作记录。" />;
  }
  return (
    <div className="space-y-3">
      {query.data?.map((item) => (
        <article key={item.id} className="panel-muted space-y-3 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="font-medium">{item.event_type}</p>
              <p className="text-sm text-[var(--text-secondary)]">
                entity: {item.entity_type} · actor: {item.actor_user_id ?? "system"}
              </p>
            </div>
            <span className="text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">
              {formatAuditTime(item.created_at)}
            </span>
          </div>
          <CodeBlock value={item.details} />
        </article>
      ))}
    </div>
  );
}
