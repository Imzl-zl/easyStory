"use client";

import { SectionCard } from "@/components/ui/section-card";

const FILE_GROUPS = [
  {
    description: "这些文件跟着当前账号走，切换账号后各自独立。Skills、Agents、Hooks、MCP 都属于这一层。",
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
    description: "项目层已经正式启用项目长期规则、项目 AI 偏好、项目 Skills 和项目 MCP；系统内置能力仍由平台统一提供。",
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
      className="border-[rgba(46,111,106,0.12)] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(242,246,244,0.94))]"
      description="参考 Claude 的文件心智：这些设置本质上是在编辑你自己的配置文件，而不是后台资源对象。"
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
    <div className="min-w-0 rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.74)] p-4 shadow-[0_12px_24px_rgba(133,118,88,0.05)]">
      <div className="space-y-2">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-[var(--text-tertiary)] uppercase">
          {index.toString().padStart(2, "0")}
        </p>
        <p className="text-sm font-semibold text-[var(--text-primary)]">{title}</p>
        <p className="text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p>
      </div>
      <div className="mt-4 min-w-0 space-y-2">
        {items.map((item) => (
          <div
            className="min-w-0 break-all rounded-[18px] border border-[rgba(255,255,255,0.72)] bg-[rgba(248,243,235,0.84)] px-3 py-2.5 font-mono text-[10px] leading-5 text-[var(--text-primary)] sm:text-[11px]"
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
    <div className="min-w-0 rounded-[20px] border border-[rgba(46,111,106,0.1)] bg-[rgba(46,111,106,0.06)] px-4 py-3">
      <p className="text-[11px] font-semibold tracking-[0.16em] text-[var(--text-tertiary)] uppercase">{label}</p>
      <div className="mt-2 min-w-0 break-all text-sm leading-6 text-[var(--text-secondary)]">{value}</div>
    </div>
  );
}
