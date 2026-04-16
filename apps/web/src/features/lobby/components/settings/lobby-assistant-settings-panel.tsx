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
    eyebrow: "主路径",
    title: "规则 + Skills + 模型连接",
  },
  {
    eyebrow: "当前作用域",
    title: "只影响你自己的默认方式",
  },
  {
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
            title="真正会影响日常对话体验的两块设置"
          />
          <AssistantPreferencesPanel
            headerAction={<AssistantHeaderBadge label="默认方式" />}
            onDirtyChange={onAssistantPreferencesDirtyChange}
          />
          <AssistantRulesEditor
            headerAction={<AssistantHeaderBadge label="长期规则" />}
            onDirtyChange={onAssistantRulesDirtyChange}
            scope="user"
            title="个人长期规则"
          />
        </div>
        <aside className="min-w-0 space-y-6 xl:sticky xl:top-6 xl:self-start">
          <AssistantSurfaceSectionLabel
            eyebrow="辅助说明"
            title="更多设置"
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
    <section className="panel-glass overflow-hidden border-accent-primary-muted">
      <div className="grid gap-6 px-5 py-5 xl:grid-cols-[minmax(0,1.16fr)_minmax(280px,0.84fr)] xl:px-8 xl:py-7">
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            <HeroPill label="我的助手" />
            <HeroPill label="个人默认层" />
          </div>
          <div className="space-y-3">
            <p className="text-[11px] font-semibold tracking-[0.24em] text-text-tertiary uppercase">
              默认协作方式
            </p>
            <h1 className="max-w-2xl text-[1.9rem] font-semibold leading-[1.15] text-text-primary xl:text-[2.3rem]">
              常用写作配置
            </h1>
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
  eyebrow,
  title,
}: Readonly<{
  eyebrow: string;
  title: string;
}>) {
  return (
    <article className="rounded-3xl bg-glass shadow-glass px-4 py-4 shadow-glass backdrop-blur-sm">
      <p className="text-[11px] font-semibold tracking-[0.18em] text-text-tertiary uppercase">{eyebrow}</p>
      <h2 className="mt-2 text-[15px] font-semibold leading-6 text-text-primary">{title}</h2>
    </article>
  );
}

function AssistantSurfaceSectionLabel({
  eyebrow,
  title,
}: Readonly<{
  eyebrow: string;
  title: string;
}>) {
  return (
    <div className="rounded-3xl bg-glass shadow-glass px-5 py-4">
      <p className="text-[11px] font-semibold tracking-[0.18em] text-text-tertiary uppercase">{eyebrow}</p>
      <h2 className="mt-2 text-[1.08rem] font-semibold text-text-primary">{title}</h2>
    </div>
  );
}

function AssistantHeaderBadge({ label }: Readonly<{ label: string }>) {
  return (
    <span className="rounded-pill border border-accent-primary-muted bg-accent-soft px-3 py-1 text-[11px] font-semibold tracking-[0.12em] text-accent-primary uppercase">
      {label}
    </span>
  );
}

function HeroPill({ label }: Readonly<{ label: string }>) {
  return (
    <span className="rounded-pill bg-glass shadow-glass px-3 py-1 text-[11px] font-semibold tracking-[0.14em] text-text-secondary uppercase">
      {label}
    </span>
  );
}
