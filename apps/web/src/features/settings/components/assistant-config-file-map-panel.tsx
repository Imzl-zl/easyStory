"use client";

import { SectionCard } from "@/components/ui/section-card";

const USER_FILES = [
  "users/<user_id>/AGENTS.md",
  "users/<user_id>/preferences.yaml",
  "users/<user_id>/skills/<skill_id>/SKILL.md",
  "users/<user_id>/agents/<agent_id>/AGENT.md",
  "users/<user_id>/hooks/<hook_id>/HOOK.yaml",
  "users/<user_id>/mcp_servers/<server_id>/MCP.yaml",
] as const;

const PROJECT_FILES = [
  "projects/<project_id>/AGENTS.md",
  "projects/<project_id>/preferences.yaml",
  "projects/<project_id>/skills/<skill_id>/SKILL.md",
  "projects/<project_id>/mcp_servers/<server_id>/MCP.yaml",
  "系统内置能力继续放在 /config/*",
] as const;

export function AssistantConfigFileMapPanel() {
  return (
    <SectionCard
      description="参考 Claude 的文件心智：这些设置本质上是在编辑你自己的配置文件，而不是后台资源对象。"
      title="配置文件层级"
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
        <PathGroup
          description="这些文件跟着当前账号走，切换账号后各自独立。Skills、Agents、Hooks、MCP 都属于这一层。"
          items={USER_FILES}
          title="用户层"
        />
        <PathGroup
          description="项目层已经正式启用项目长期规则、项目 AI 偏好、项目 Skills 和项目 MCP；系统内置能力仍由平台统一提供。"
          items={PROJECT_FILES}
          title="项目层 / 系统层"
        />
      </div>
      <div className="rounded-[20px] border border-[rgba(46,111,106,0.12)] bg-[rgba(46,111,106,0.05)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        运行时目录根路径为 <code>apps/api/.runtime/assistant-config/</code>。Web 设置页负责帮你写这些文件，聊天运行时再按作用域自动读取；项目层内容会优先于用户层生效。
      </div>
    </SectionCard>
  );
}

function PathGroup({
  description,
  items,
  title,
}: Readonly<{
  description: string;
  items: readonly string[];
  title: string;
}>) {
  return (
    <div className="rounded-[22px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] p-4">
      <p className="text-sm font-medium text-[var(--text-primary)]">{title}</p>
      <p className="mt-2 text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p>
      <div className="mt-4 space-y-2">
        {items.map((item) => (
          <div
            className="rounded-[16px] bg-[rgba(248,243,235,0.84)] px-3 py-2.5 font-mono text-[11px] leading-5 text-[var(--text-primary)]"
            key={item}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
