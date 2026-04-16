"use client";

import { SectionCard } from "@/components/ui/section-card";

const FILE_GROUPS = [
  {
    description: "跟随当前账号，切换账号后各自独立。",
    items: [
      "users/<user_id>/AGENTS.md",
      "users/<user_id>/preferences.yaml",
      "users/<user_id>/skills/<skill_id>/SKILL.md",
      "users/<user_id>/agents/<agent_id>/AGENT.md",
      "users/<user_id>/hooks/<hook_id>/HOOK.yaml",
      "users/<user_id>/mcp_servers/<server_id>/MCP.yaml",
    ],
    title: "用户层",
  },
  {
    description: "项目专属配置，系统内置能力由平台统一提供。",
    items: [
      "projects/<project_id>/AGENTS.md",
      "projects/<project_id>/preferences.yaml",
      "projects/<project_id>/skills/<skill_id>/SKILL.md",
      "projects/<project_id>/mcp_servers/<server_id>/MCP.yaml",
      "系统内置能力继续放在 /config/*",
    ],
    title: "项目层 / 系统层",
  },
] as const;

export function AssistantConfigFileMapPanel() {
  return (
    <SectionCard
      bodyClassName="space-y-4"
      className="border-accent-primary-muted bg-[var(--bg-config-file-gradient)]"
      title="文件层级与生效顺序"
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {FILE_GROUPS.map((group, index) => (
          <PathGroup
            description={group.description}
            index={index + 1}
            items={group.items}
            key={group.title}
            title={group.title}
          />
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <FactCard
          label="目录根路径"
          value={<code className="font-mono text-[11px]">apps/api/.runtime/assistant-config/</code>}
        />
        <FactCard label="覆盖规则" value="项目层内容优先于用户层生效。" />
        <FactCard label="系统能力" value="系统内置配置继续由 /config/* 提供。" />
      </div>
    </SectionCard>
  );
}

function PathGroup({
  description,
  index,
  items,
  title,
}: Readonly<{
  description: string;
  index: number;
  items: readonly string[];
  title: string;
}>) {
  return (
    <div className="min-w-0 rounded-3xl bg-glass shadow-glass-heavy p-4">
      <div className="space-y-2">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-text-tertiary uppercase">
          {index.toString().padStart(2, "0")}
        </p>
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        <p className="text-[12px] leading-5 text-text-secondary">{description}</p>
      </div>
      <div className="mt-4 min-w-0 space-y-2">
        {items.map((item) => (
          <div
            className="min-w-0 break-all rounded-2xl border border-white/72 bg-glass px-3 py-2.5 font-mono text-[10px] leading-5 text-text-primary sm:text-[11px]"
            key={item}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

function FactCard({
  label,
  value,
}: Readonly<{
  label: string;
  value: React.ReactNode;
}>) {
  return (
    <div className="min-w-0 rounded-2xl border border-accent-primary/10 bg-accent-soft px-4 py-3">
      <p className="text-[11px] font-semibold tracking-[0.16em] text-text-tertiary uppercase">{label}</p>
      <div className="mt-2 min-w-0 break-all text-sm leading-6 text-text-secondary">{value}</div>
    </div>
  );
}
