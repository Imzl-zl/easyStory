"use client";

import Link from "next/link";

type LobbyEntryCardProps = {
  feedback: string | null;
  templatesLoading: boolean;
  templateCount: number;
  templatePreviewNames: string[];
  templatesError: string | null;
};

export function LobbyEntryCard({
  feedback,
  templatesLoading,
  templateCount,
  templatePreviewNames,
  templatesError,
}: LobbyEntryCardProps) {
  return (
    <section className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">Incubator</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          模板问答、自由描述和模板建项目已经独立出来，Lobby 不再内联承担创建状态。
        </p>
      </div>
      <dl className="grid gap-3 text-sm text-[var(--text-secondary)]">
        <div className="flex justify-between gap-4">
          <dt>可用模板</dt>
          <dd>{templatesLoading ? "加载中..." : templateCount}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>推荐入口</dt>
          <dd>模板问答 / 自由描述</dd>
        </div>
      </dl>
      {templatePreviewNames.length > 0 ? (
        <p className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
          最近可用模板：{templatePreviewNames.join(" / ")}
        </p>
      ) : null}
      {templatesError ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {templatesError}
        </div>
      ) : null}
      {feedback ? (
        <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
          {feedback}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Link className="ink-button flex-1 justify-center" href="/workspace/lobby/new">
          进入 Incubator
        </Link>
        <Link className="ink-button-secondary flex-1 justify-center" href="/workspace/lobby/templates">
          模板库
        </Link>
      </div>
    </section>
  );
}
