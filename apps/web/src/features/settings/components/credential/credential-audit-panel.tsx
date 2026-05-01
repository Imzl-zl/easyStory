"use client";

import { useQuery } from "@tanstack/react-query";

import { CodeBlock } from "@/components/ui/code-block";
import { formatAuditTime } from "@/features/settings/components/credential/credential-center-display-support";
import { getErrorMessage } from "@/lib/api/client";
import { listCredentialAuditLogs } from "@/lib/api/observability";

export function CredentialAuditPanel({ credentialId }: { credentialId: string | null }) {
  const query = useQuery({
    queryKey: ["credential-audit", credentialId],
    queryFn: () => listCredentialAuditLogs(credentialId as string),
    enabled: Boolean(credentialId),
  });

  if (!credentialId) {
    return (
      <div className="rounded-lg px-6 py-8 text-center" style={{ background: "var(--bg-canvas)", border: "1px dashed var(--line-medium)" }}>
        <p className="text-[13px] font-medium" style={{ color: "var(--text-secondary)" }}>选择一条连接</p>
        <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>点击左侧列表中的连接查看审计日志</p>
      </div>
    );
  }

  if (query.isLoading) {
    return (
      <div className="rounded-lg px-4 py-5 text-[13px]" style={{ background: "var(--bg-canvas)", color: "var(--text-tertiary)", border: "1px solid var(--line-soft)" }}>
        正在加载审计日志…
      </div>
    );
  }

  if (query.error) {
    return (
      <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
        {getErrorMessage(query.error)}
      </div>
    );
  }

  if ((query.data?.length ?? 0) === 0) {
    return (
      <div className="rounded-lg px-6 py-8 text-center" style={{ background: "var(--bg-canvas)", border: "1px dashed var(--line-medium)" }}>
        <p className="text-[13px] font-medium" style={{ color: "var(--text-secondary)" }}>暂无审计日志</p>
        <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>这条连接还没有操作记录</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-semibold tracking-[0.1em] uppercase" style={{ color: "var(--accent-primary)" }}>
          操作记录
        </span>
        <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
          {query.data?.length} 条
        </span>
      </div>
      {query.data?.map((item) => (
        <article
          key={item.id}
          className="rounded-md p-3 space-y-2"
          style={{
            background: "var(--bg-canvas)",
            border: "1px solid var(--line-soft)",
          }}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[11px] font-medium truncate" style={{ color: "var(--text-primary)" }}>
                {item.event_type}
              </span>
              <span className="text-[9px] flex-shrink-0 px-1 py-0.5 rounded" style={{ background: "var(--line-soft)", color: "var(--text-tertiary)" }}>
                {item.entity_type}
              </span>
            </div>
            <span className="text-[9px] flex-shrink-0" style={{ color: "var(--text-tertiary)" }}>
              {formatAuditTime(item.created_at)}
            </span>
          </div>
          <CodeBlock value={item.details} />
        </article>
      ))}
    </div>
  );
}
