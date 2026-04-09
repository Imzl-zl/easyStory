"use client";

import { AssistantConfigFileMapPanel } from "@/features/settings/components/assistant/common/assistant-config-file-map-panel";
import { AssistantGettingStartedPanel } from "@/features/settings/components/assistant/common/assistant-getting-started-panel";
import { AssistantPreferencesPanel } from "@/features/settings/components/assistant/preferences/assistant-preferences-panel";
import { AssistantRulesEditor } from "@/features/settings/components/assistant/rules/assistant-rules-editor";

type LobbyAssistantSettingsPanelProps = {
  onAssistantPreferencesDirtyChange: (isDirty: boolean) => void;
  onAssistantRulesDirtyChange: (isDirty: boolean) => void;
  onOpenCredentials: () => void;
  onOpenSkills: () => void;
};

const HERO_METRICS = [
  {
    description: "先把新聊天的默认协作方式调顺，再决定是否要固定角色或接外部工具。",
    eyebrow: "主路径",
    title: "规则 + Skills + 模型连接",
  },
  {
    description: "这个页面只改个人层默认值。项目专属规则和偏好，仍然放在项目设置里。",
    eyebrow: "当前作用域",
    title: "只影响你自己的默认方式",
  },
  {
    description: "Agents、Hooks、MCP 继续保留，但应该在主路径稳定之后再逐步打开。",
    eyebrow: "高级能力",
    title: "按需补，不要一开始铺满",
  },
] as const;

export function LobbyAssistantSettingsPanel({
  onAssistantPreferencesDirtyChange,
  onAssistantRulesDirtyChange,
  onOpenCredentials,
  onOpenSkills,
}: Readonly<LobbyAssistantSettingsPanelProps>) {
  return (
    <div className="space-y-6">
      <AssistantSurfaceHero onOpenCredentials={onOpenCredentials} onOpenSkills={onOpenSkills} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.72fr)] 2xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <AssistantSurfaceSectionLabel
            eyebrow="主编辑区"
            description="先调默认连接和长期规则，决定新聊天怎样开始、默认用什么方式配合你。"
            title="真正会影响日常对话体验的两块设置"
          />
          <AssistantPreferencesPanel
            headerAction={<AssistantHeaderBadge label="默认方式" />}
            onDirtyChange={onAssistantPreferencesDirtyChange}
          />
          <AssistantRulesEditor
            description="保存后，新聊天会自动带上这些规则。"
            headerAction={<AssistantHeaderBadge label="长期规则" />}
            onDirtyChange={onAssistantRulesDirtyChange}
            scope="user"
            title="个人长期规则"
          />
        </div>
        <aside className="min-w-0 space-y-6 xl:sticky xl:top-6 xl:self-start">
          <AssistantSurfaceSectionLabel
            eyebrow="辅助说明"
            description="把跳转入口、文件层级和高阶能力都放在右侧，避免和主编辑区互相抢视觉注意力。"
            title="先看路径，再决定要不要继续扩展"
          />
          <AssistantGettingStartedPanel
            onOpenCredentials={onOpenCredentials}
            onOpenSkills={onOpenSkills}
          />
          <AssistantConfigFileMapPanel />
        </aside>
      </div>
    </div>
  );
}

function AssistantSurfaceHero({
  onOpenCredentials,
  onOpenSkills,
}: Readonly<{
  onOpenCredentials: () => void;
  onOpenSkills: () => void;
}>) {
  return (
    <section className="panel-shell overflow-hidden border-[rgba(46,111,106,0.14)] bg-[linear-gradient(135deg,rgba(255,250,243,0.96),rgba(244,238,228,0.94)_54%,rgba(233,242,238,0.9))]">
      <div className="grid gap-6 px-5 py-5 xl:grid-cols-[minmax(0,1.16fr)_minmax(280px,0.84fr)] xl:px-8 xl:py-7">
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            <HeroPill label="我的助手" />
            <HeroPill label="个人默认层" />
          </div>
          <div className="space-y-3">
            <p className="text-[11px] font-semibold tracking-[0.24em] text-[var(--text-tertiary)] uppercase">
              默认协作方式
            </p>
            <h1 className="max-w-2xl text-[1.9rem] font-semibold leading-[1.15] text-[var(--text-primary)] xl:text-[2.3rem]">
              先把每天都会用到的默认体验定稳，再慢慢补高阶能力。
            </h1>
            <p className="max-w-2xl text-sm leading-7 text-[var(--text-secondary)] xl:text-[15px]">
              这页的目标不是把所有配置一次性铺满，而是先让新聊天的默认连接、默认模型、长期规则和常用
              Skills 形成一条清晰主路径。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="ink-button-secondary h-10 px-4" onClick={onOpenSkills} type="button">
              管理 Skills
            </button>
            <button className="ink-button-secondary h-10 px-4" onClick={onOpenCredentials} type="button">
              管理模型连接
            </button>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          {HERO_METRICS.map((item) => (
            <AssistantSummaryMetric
              description={item.description}
              eyebrow={item.eyebrow}
              key={item.title}
              title={item.title}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function AssistantSummaryMetric({
  description,
  eyebrow,
  title,
}: Readonly<{
  description: string;
  eyebrow: string;
  title: string;
}>) {
  return (
    <article className="rounded-[24px] border border-[rgba(255,255,255,0.7)] bg-[rgba(255,255,255,0.76)] px-4 py-4 shadow-[0_16px_30px_rgba(133,118,88,0.08)] backdrop-blur">
      <p className="text-[11px] font-semibold tracking-[0.18em] text-[var(--text-tertiary)] uppercase">{eyebrow}</p>
      <h2 className="mt-2 text-[15px] font-semibold leading-6 text-[var(--text-primary)]">{title}</h2>
      <p className="mt-2 text-[12px] leading-6 text-[var(--text-secondary)]">{description}</p>
    </article>
  );
}

function AssistantSurfaceSectionLabel({
  description,
  eyebrow,
  title,
}: Readonly<{
  description: string;
  eyebrow: string;
  title: string;
}>) {
  return (
    <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] px-5 py-4">
      <p className="text-[11px] font-semibold tracking-[0.18em] text-[var(--text-tertiary)] uppercase">{eyebrow}</p>
      <h2 className="mt-2 text-[1.08rem] font-semibold text-[var(--text-primary)]">{title}</h2>
      <p className="mt-2 max-w-3xl text-[13px] leading-6 text-[var(--text-secondary)]">{description}</p>
    </div>
  );
}

function AssistantHeaderBadge({ label }: Readonly<{ label: string }>) {
  return (
    <span className="rounded-full border border-[rgba(46,111,106,0.14)] bg-[rgba(46,111,106,0.08)] px-3 py-1 text-[11px] font-semibold tracking-[0.12em] text-[var(--text-secondary)] uppercase">
      {label}
    </span>
  );
}

function HeroPill({ label }: Readonly<{ label: string }>) {
  return (
    <span className="rounded-full border border-[rgba(46,111,106,0.12)] bg-[rgba(255,255,255,0.72)] px-3 py-1 text-[11px] font-semibold tracking-[0.14em] text-[var(--text-secondary)] uppercase">
      {label}
    </span>
  );
}
