"use client";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import type { ConfigRegistryDetail, ConfigRegistryType } from "@/lib/api/types";

import { buildConfigRegistryDetailRows } from "./config-registry-support";

type ConfigRegistryDetailPanelProps = {
  detail: ConfigRegistryDetail | null;
  errorMessage: string | null;
  isLoading: boolean;
  type: ConfigRegistryType;
};

export function ConfigRegistryDetailPanel({
  detail,
  errorMessage,
  isLoading,
  type,
}: Readonly<ConfigRegistryDetailPanelProps>) {
  if (errorMessage && !detail) {
    return (
      <Banner tone="danger" message={errorMessage} />
    );
  }
  if (isLoading && !detail) {
    return <Banner tone="muted" message="正在加载内容…" />;
  }
  if (!detail) {
    return (
      <EmptyState
        title="选择配置项"
        description="从左侧查看详情。"
      />
    );
  }

  const rows = buildConfigRegistryDetailRows(type, detail);
  const tags = "tags" in detail && Array.isArray(detail.tags) ? detail.tags : [];

  return (
    <div className="space-y-4">
      {errorMessage ? <Banner tone="danger" message={errorMessage} /> : null}
      <section className="panel-muted space-y-4 p-5">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">
            当前内容
          </p>
          <h3 className="font-serif text-xl font-semibold">{detail.name}</h3>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            {detail.description ?? "暂无描述。"}
          </p>
        </div>
        <dl className="grid gap-3 sm:grid-cols-2">
          <DetailRow label="编号" value={detail.id} />
          <DetailRow label="版本" value={detail.version} />
          <DetailRow label="作者" value={detail.author ?? "未标注"} />
          {rows.map((row) => (
            <DetailRow key={row.label} label={row.label} value={row.value} />
          ))}
        </dl>
        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-[rgba(46,111,106,0.08)] px-3 py-1 text-xs text-[var(--accent-ink)]"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </section>
      <section className="panel-muted space-y-3 p-5">
        <div className="space-y-1">
          <h4 className="font-serif text-lg font-semibold">完整配置</h4>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            用于核对完整字段。
          </p>
        </div>
        <CodeBlock value={detail} />
      </section>
    </div>
  );
}

function DetailRow({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.56)] px-4 py-3">
      <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">{label}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--text-primary)]">{value}</p>
    </div>
  );
}

function Banner({
  message,
  tone,
}: Readonly<{
  message: string;
  tone: "danger" | "muted";
}>) {
  if (tone === "danger") {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {message}
      </div>
    );
  }
  return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{message}</div>;
}
