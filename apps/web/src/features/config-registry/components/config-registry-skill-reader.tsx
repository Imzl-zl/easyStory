"use client";

import { useState } from "react";

import type { SkillConfigDetail } from "@/lib/api/types";

import {
  buildSkillMarkdown,
  buildSkillModelDocument,
  buildSkillResourceItems,
  buildSkillSchemaDocument,
  type SkillResourceKey,
} from "./config-registry-skill-reader-support";

export function ConfigRegistrySkillReader({
  detail,
}: Readonly<{
  detail: SkillConfigDetail;
}>) {
  const resources = buildSkillResourceItems(detail);
  const [activeKey, setActiveKey] = useState<SkillResourceKey>("skill-markdown");
  const activeResource = resources.find((item) => item.key === activeKey) ?? resources[0];

  return (
    <div className="space-y-4">
      <section className="panel-muted space-y-5 p-5">
        <header className="space-y-4">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-[0.18em] text-accent-primary">Skill 说明视图</p>
            <h3 className="font-serif text-xl font-semibold text-text-primary">{detail.name}</h3>
            <p className="text-sm leading-6 text-text-secondary">
              {detail.description ?? "当前还没有补充说明。"}
            </p>
          </div>
          <div className="callout-info px-4 py-3">
            <p className="text-sm font-medium text-text-primary">这里优先按文件式 Skill 展示。</p>
            <p className="mt-1 text-sm leading-6 text-text-secondary">
              下方除 <code>SKILL.md</code> 外，其余文件都是系统根据当前运行配置生成的预览，不代表仓库里已经存在这些真实文件。
            </p>
          </div>
          <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetaCard label="编号" value={detail.id} />
            <MetaCard label="分类" value={detail.category} />
            <MetaCard label="版本" value={detail.version} />
            <MetaCard label="标签" value={detail.tags.length > 0 ? detail.tags.join("、") : "未设置"} />
          </dl>
        </header>
      </section>

      <section className="panel-muted p-4">
        <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="rounded-2xl bg-muted shadow-sm p-3">
            <p className="px-2 pb-2 text-xs uppercase tracking-[0.18em] text-text-secondary">说明与运行文件</p>
            <div className="space-y-1.5">
              {resources.map((resource) => (
                <button
                  key={resource.key}
                  className={[
                    "w-full rounded-2xl border px-3 py-2.5 text-left transition-colors",
                    resource.key === activeResource?.key
                      ? "border-accent-primary-muted bg-accent-soft ring-1 ring-inset ring-line-soft"
                      : "border-transparent hover:border-accent-primary-muted hover:bg-accent-soft",
                  ].join(" ")}
                  type="button"
                  onClick={() => setActiveKey(resource.key)}
                >
                  <p
                    className={`text-sm font-medium ${
                      resource.key === activeResource?.key ? "text-accent-primary" : "text-text-primary"
                    }`}
                  >
                    {resource.filename}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-text-secondary">{resource.description}</p>
                </button>
              ))}
            </div>
          </aside>

          <div className="rounded-2xl bg-glass shadow-glass">
            <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line-soft px-4 py-3">
              <div className="space-y-1">
                <p className="text-sm font-medium text-text-primary">{activeResource?.filename}</p>
                <p className="text-sm leading-6 text-text-secondary">{activeResource?.description}</p>
              </div>
              <SkillPill
                label={activeResource?.key === "skill-markdown" ? "主入口" : "附属资源"}
                tone={activeResource?.key === "skill-markdown" ? "accent" : "muted"}
              />
            </header>
            <div className="px-4 py-4">
              <pre className="mono-block max-h-[42rem] min-h-[28rem] whitespace-pre-wrap break-words">
                {renderSkillDocument(detail, activeResource?.key ?? "skill-markdown")}
              </pre>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function MetaCard({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="rounded-2xl bg-muted shadow-sm px-4 py-3">
      <p className="text-xs uppercase tracking-[0.16em] text-text-secondary">{label}</p>
      <p className="mt-2 text-sm leading-6 text-text-primary">{value}</p>
    </div>
  );
}

function SkillPill({
  label,
  tone,
}: Readonly<{
  label: string;
  tone: "accent" | "muted";
}>) {
  const className =
    tone === "accent"
      ? "bg-accent-primary/10 text-accent-primary"
      : "bg-line-strong text-text-secondary";
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs tracking-[0.08em] ${className}`}>
      {label}
    </span>
  );
}

function renderSkillDocument(detail: SkillConfigDetail, resourceKey: SkillResourceKey) {
  if (resourceKey === "schema") {
    return buildSkillSchemaDocument(detail);
  }
  if (resourceKey === "model-config") {
    return buildSkillModelDocument(detail.model);
  }
  if (resourceKey === "raw-config") {
    return JSON.stringify(detail, null, 2);
  }
  return buildSkillMarkdown(detail);
}
