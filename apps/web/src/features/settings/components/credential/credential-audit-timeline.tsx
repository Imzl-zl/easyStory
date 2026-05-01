"use client";

import { useQuery } from "@tanstack/react-query";

import { CodeBlock } from "@/components/ui/code-block";
import { formatAuditTime } from "@/features/settings/components/credential/credential-center-display-support";
import { getErrorMessage } from "@/lib/api/client";
import { listCredentialAuditLogs } from "@/lib/api/observability";
import type { CredentialView } from "@/lib/api/types";

export function CredentialAuditTimeline({
  credentialId,
  credentials,
  onSelectCredential,
}: {
  credentialId: string | null;
  credentials: CredentialView[];
  onSelectCredential: (id: string) => void;
}) {
  const query = useQuery({
    queryKey: ["credential-audit", credentialId],
    queryFn: () => listCredentialAuditLogs(credentialId as string),
    enabled: Boolean(credentialId),
  });

  return (
    <div className="max-w-3xl mx-auto">
      {/* Credential Filter */}
      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
        <span className="text-[10px] font-semibold tracking-[0.1em] uppercase flex-shrink-0" style={{ color: "var(--accent-primary)" }}>
          筛选
        </span>
        {credentials.map((c) => (
          <button
            key={c.id}
            className="px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex-shrink-0"
            onClick={() => onSelectCredential(c.id)}
            style={{
              background: credentialId === c.id ? "var(--line-medium)" : "var(--bg-canvas)",
              color: credentialId === c.id ? "var(--text-primary)" : "var(--text-tertiary)",
              border: "1px solid var(--line-soft)",
            }}
          >
            {c.display_name}
          </button>
        ))}
      </div>

      {/* Timeline */}
      {!credentialId ? (
        <div className="text-center py-12">
          <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>选择一条连接查看审计日志</p>
        </div>
      ) : query.isLoading ? (
        <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>正在加载审计日志…</p>
      ) : query.error ? (
        <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
          {getErrorMessage(query.error)}
        </div>
      ) : (query.data?.length ?? 0) === 0 ? (
        <div className="text-center py-12">
          <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>暂无审计日志</p>
          <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>这条连接还没有操作记录</p>
        </div>
      ) : (
        <div className="space-y-3">
          {query.data?.map((item, index) => (
            <div key={item.id} className="flex gap-3">
              {/* Timeline Line */}
              <div className="flex flex-col items-center">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ background: index === 0 ? "var(--accent-primary)" : "var(--text-tertiary)" }}
                />
                {index < (query.data?.length ?? 0) - 1 && (
                  <div className="w-px flex-1 mt-1" style={{ background: "var(--bg-surface)" }} />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 pb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
                    {item.event_type}
                  </span>
                  <span className="text-[9px] px-1 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}>
                    {item.entity_type}
                  </span>
                  <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                    {formatAuditTime(item.created_at)}
                  </span>
                </div>
                <CodeBlock value={item.details} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
