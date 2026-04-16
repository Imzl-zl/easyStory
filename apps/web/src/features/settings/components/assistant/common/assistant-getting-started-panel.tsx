"use client";

import { SectionCard } from "@/components/ui/section-card";

const QUICK_START_STEPS = [
  {
    description: "决定每次聊天默认怎么配合你。",
    title: "个人长期规则",
  },
  {
    description: "把常用聊天方式保存成自己的 SKILL.md。",
    title: "Skills",
  },
  {
    description: "设置默认连接、默认模型和回复上限。",
    title: "模型连接",
  },
] as const;

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
      className="border-accent-primary-muted bg-[var(--bg-getting-started-gradient)]"
      title="默认协作方式"
    >
      <div className="space-y-3">
        <StepCard
          description={QUICK_START_STEPS[0].description}
          index="01"
          title={QUICK_START_STEPS[0].title}
        />
        <StepCard
          action={
            <button className="ink-button-secondary h-9 px-4" type="button" onClick={onOpenSkills}>
              打开 Skills
            </button>
          }
          description={QUICK_START_STEPS[1].description}
          index="02"
          title={QUICK_START_STEPS[1].title}
        />
        <StepCard
          action={
            <button className="ink-button-secondary h-9 px-4" type="button" onClick={onOpenCredentials}>
              打开模型连接
            </button>
          }
          description={QUICK_START_STEPS[2].description}
          index="03"
          title={QUICK_START_STEPS[2].title}
        />
      </div>
      <div className="rounded-3xl border border-accent-primary-muted bg-accent-soft px-4 py-4">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-text-tertiary uppercase">高阶能力</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <CapabilityTag label="Agents 固定角色" />
          <CapabilityTag label="Hooks 自动动作" />
          <CapabilityTag label="MCP 外部工具" />
        </div>
      </div>
    </SectionCard>
  );
}

function StepCard({
  action,
  description,
  index,
  title,
}: Readonly<{
  action?: React.ReactNode;
  description: string;
  index: string;
  title: string;
}>) {
  return (
    <article className="rounded-3xl bg-glass shadow-glass-heavy px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-[11px] font-semibold tracking-[0.16em] text-text-tertiary uppercase">
            Step {index}
          </p>
          <h3 className="text-[15px] font-semibold text-text-primary">{title}</h3>
        </div>
      </div>
      <p className="mt-3 text-[13px] leading-6 text-text-secondary">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </article>
  );
}

function CapabilityTag({ label }: Readonly<{ label: string }>) {
  return (
    <span className="rounded-pill bg-surface shadow-xs px-3 py-1 text-[11px] font-semibold text-text-secondary">
      {label}
    </span>
  );
}
