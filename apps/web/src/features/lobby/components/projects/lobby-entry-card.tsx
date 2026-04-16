"use client";

import Link from "next/link";

type LobbyEntryCardProps = {
  templatesLoading: boolean;
  templateCount: number;
  templatePreviewNames: string[];
  templatesError: string | null;
};

export function LobbyEntryCard({
  templatesLoading,
  templateCount,
  templatePreviewNames,
  templatesError,
}: LobbyEntryCardProps) {
  return (
    <section className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">新建项目</h3>
        <p className="text-sm leading-6 text-text-secondary">
          通过 AI 聊天或模板创建项目。
        </p>
      </div>
      <dl className="grid gap-3 text-sm text-text-secondary">
        <div className="flex justify-between gap-4">
          <dt>可用模板</dt>
          <dd>{templatesLoading ? "加载中…" : templateCount}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>开始方式</dt>
          <dd>AI 聊天 / 模板创建</dd>
        </div>
      </dl>
      {templatePreviewNames.length > 0 ? (
        <p className="rounded-2xl bg-muted px-4 py-3 text-sm leading-6 text-text-secondary">
          最近常用模板：{templatePreviewNames.join(" / ")}
        </p>
      ) : null}
      {templatesError ? (
        <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
          {templatesError}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Link className="ink-button flex-1 justify-center" href="/workspace/lobby/new">
          AI 聊天
        </Link>
        <Link className="ink-button-secondary flex-1 justify-center" href="/workspace/lobby/templates">
          模板库
        </Link>
      </div>
    </section>
  );
}
