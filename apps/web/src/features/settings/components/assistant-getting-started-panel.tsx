"use client";

import { SectionCard } from "@/components/ui/section-card";

type AssistantGettingStartedPanelProps = {
  onOpenCredentials: () => void;
  onOpenSkills: () => void;
};

export function AssistantGettingStartedPanel({
  onOpenCredentials,
  onOpenSkills,
}: Readonly<AssistantGettingStartedPanelProps>) {
  return (
    <SectionCard
      description="大多数时候，先把长期规则、聊天方式和模型连接定下来就够了。"
      title="先从这 3 项开始"
    >
      <div className="grid gap-3 xl:grid-cols-[repeat(3,minmax(0,1fr))]">
        <StepCard
          description="决定每次聊天默认怎么配合你。这页下面就能直接改。"
          title="1. 个人长期规则"
        />
        <StepCard
          action={
            <button className="ink-button-secondary" type="button" onClick={onOpenSkills}>
              打开 Skills
            </button>
          }
          description="把常用聊天方式保存成自己的 SKILL.md，新聊天优先从这里切换。"
          title="2. Skills"
        />
        <StepCard
          action={
            <button className="ink-button-secondary" type="button" onClick={onOpenCredentials}>
              打开模型连接
            </button>
          }
          description="设置默认连接、默认模型和回复上限，平时只需要保持可用即可。"
          title="3. 模型连接"
        />
      </div>
      <div className="rounded-[20px] border border-[rgba(46,111,106,0.12)] bg-[rgba(46,111,106,0.05)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        Agents、Hooks、MCP 也都是你自己的配置，只是大多数时候不用一开始全配满。等你想固定助手角色、自动多做一步，或者连接外部工具时，再去补上就行。
      </div>
    </SectionCard>
  );
}

function StepCard({
  action,
  description,
  title,
}: Readonly<{
  action?: React.ReactNode;
  description: string;
  title: string;
}>) {
  return (
    <div className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.7)] px-4 py-4">
      <p className="text-sm font-medium text-[var(--text-primary)]">{title}</p>
      <p className="mt-2 text-[13px] leading-6 text-[var(--text-secondary)]">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
