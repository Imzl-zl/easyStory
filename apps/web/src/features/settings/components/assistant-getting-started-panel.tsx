"use client";

import { SectionCard } from "@/components/ui/section-card";

const QUICK_START_STEPS = [
  {
    description: "决定每次聊天默认怎么配合你。这页下面就能直接改。",
    hint: "就在下方编辑",
    title: "个人长期规则",
  },
  {
    description: "把常用聊天方式保存成自己的 SKILL.md，新聊天优先从这里切换。",
    title: "Skills",
  },
  {
    description: "设置默认连接、默认模型和回复上限，平时只需要保持可用即可。",
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
      className="border-[rgba(46,111,106,0.12)] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(243,240,232,0.94))]"
      description="大多数时候，只要先把长期规则、Skills 和模型连接排成顺手的一条主路径就够了。"
      title="先把默认协作方式排成一条顺手主路径"
    >
      <div className="space-y-3">
        <StepCard
          description={QUICK_START_STEPS[0].description}
          index="01"
          hint={QUICK_START_STEPS[0].hint}
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
      <div className="rounded-[24px] border border-[rgba(46,111,106,0.12)] bg-[rgba(46,111,106,0.06)] px-4 py-4">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-[var(--text-tertiary)] uppercase">高阶能力</p>
        <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
          Agents、Hooks、MCP 也都是你自己的配置，只是大多数时候不用一开始全配满。等你想固定助手角色、自动多做一步，或者连接外部工具时，再去补上就行。
        </p>
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
  hint,
  index,
  title,
}: Readonly<{
  action?: React.ReactNode;
  description: string;
  hint?: string;
  index: string;
  title: string;
}>) {
  return (
    <article className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.76)] px-4 py-4 shadow-[0_10px_24px_rgba(133,118,88,0.05)]">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-[11px] font-semibold tracking-[0.16em] text-[var(--text-tertiary)] uppercase">
            Step {index}
          </p>
          <h3 className="text-[15px] font-semibold text-[var(--text-primary)]">{title}</h3>
        </div>
        {hint ? (
          <span className="rounded-full bg-[rgba(46,111,106,0.08)] px-3 py-1 text-[11px] font-semibold text-[var(--text-secondary)]">
            {hint}
          </span>
        ) : null}
      </div>
      <p className="mt-3 text-[13px] leading-6 text-[var(--text-secondary)]">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </article>
  );
}

function CapabilityTag({ label }: Readonly<{ label: string }>) {
  return (
    <span className="rounded-full border border-[rgba(46,111,106,0.12)] bg-[rgba(255,255,255,0.74)] px-3 py-1 text-[11px] font-semibold text-[var(--text-secondary)]">
      {label}
    </span>
  );
}
