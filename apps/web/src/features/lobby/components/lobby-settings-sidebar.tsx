"use client";

import { GuardedLink } from "@/components/ui/guarded-link";
import { SectionCard } from "@/components/ui/section-card";
import type { LobbySettingsTab } from "@/features/lobby/components/lobby-settings-support";

const PRIMARY_NAV_ITEMS = [
  { description: "长期规则、默认方式", label: "AI 助手", tab: "assistant" },
  { description: "保存常用聊天方式", label: "Skills", tab: "skills" },
  { description: "选择默认连接和模型", label: "模型连接", tab: "credentials" },
] as const;

const ADVANCED_NAV_ITEMS = [
  { description: "进阶：固定助手角色", label: "Agents", tab: "agents" },
  { description: "进阶：自动动作", label: "Hooks", tab: "hooks" },
  { description: "进阶：外部工具连接", label: "MCP", tab: "mcp" },
] as const;

type LobbySettingsSidebarProps = {
  isDirty: boolean;
  isPending: boolean;
  onNavigateAway: (onConfirm: () => void) => void;
  onSelectTab: (tab: LobbySettingsTab) => void;
  tab: LobbySettingsTab;
};

export function LobbySettingsSidebar({
  isDirty,
  isPending,
  onNavigateAway,
  onSelectTab,
  tab,
}: Readonly<LobbySettingsSidebarProps>) {
  return (
    <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
      <SectionCard
        bodyClassName="space-y-5"
        className="border-[rgba(46,111,106,0.14)] bg-[linear-gradient(180deg,rgba(255,250,243,0.94),rgba(255,255,255,0.98)_38%,rgba(243,240,232,0.94))]"
        action={
          <GuardedLink
            className="ink-button-secondary"
            href="/workspace/lobby"
            isDirty={isDirty}
            onNavigate={onNavigateAway}
          >
            返回项目大厅
          </GuardedLink>
        }
        description="先完成长期规则、Skills 和模型连接；进阶能力按需要再添加。"
        title="AI 设置"
      >
        <LobbySettingsNavGroup
          description="先把每天都会用到的默认协作方式定稳，再决定是否继续往下扩展。"
          items={PRIMARY_NAV_ITEMS}
          isPending={isPending}
          onSelectTab={onSelectTab}
          tab={tab}
          title="主路径"
        />
        <LobbySettingsNavGroup
          description="这些能力保留给更细的控制需求，不必一开始全部配置。"
          items={ADVANCED_NAV_ITEMS}
          isPending={isPending}
          onSelectTab={onSelectTab}
          tab={tab}
          title="高级能力"
        />
      </SectionCard>
      <div className="panel-muted space-y-2 px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-[var(--text-tertiary)] uppercase">作用域</p>
        <p>这里只管理你自己的默认设置。</p>
        <p>项目专属规则请前往“项目设置”。</p>
      </div>
    </aside>
  );
}

function LobbySettingsNavGroup({
  description,
  isPending,
  items,
  onSelectTab,
  tab,
  title,
}: Readonly<{
  description: string;
  isPending: boolean;
  items: readonly { description: string; label: string; tab: LobbySettingsTab }[];
  onSelectTab: (tab: LobbySettingsTab) => void;
  tab: LobbySettingsTab;
  title: string;
}>) {
  return (
    <section className="space-y-3">
      <div className="space-y-1 px-1">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-[var(--text-tertiary)] uppercase">{title}</p>
        <p className="text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <LobbySettingsNavButton
            active={tab === item.tab}
            description={item.description}
            disabled={isPending}
            key={item.tab}
            label={item.label}
            onClick={() => onSelectTab(item.tab)}
          />
        ))}
      </div>
    </section>
  );
}

function LobbySettingsNavButton({
  active,
  description,
  disabled,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  description: string;
  disabled: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={[
        "w-full rounded-[22px] border px-4 py-4 text-left transition",
        active
          ? "border-[rgba(46,111,106,0.2)] bg-[rgba(46,111,106,0.08)] shadow-[0_12px_24px_rgba(90,122,107,0.08)]"
          : "border-[var(--line-soft)] bg-[rgba(255,255,255,0.58)] hover:border-[var(--line-strong)] hover:bg-[rgba(255,255,255,0.84)]",
      ].join(" ")}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <span className="flex items-start justify-between gap-3">
        <span className="flex flex-col items-start gap-1">
          <span className="text-sm font-semibold text-[var(--text-primary)]">{label}</span>
          <span className="text-[12px] leading-5 text-[var(--text-secondary)]">{description}</span>
        </span>
        <span
          className={[
            "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-[0.12em] uppercase",
            active
              ? "bg-[rgba(46,111,106,0.12)] text-[var(--text-primary)]"
              : "bg-[rgba(255,255,255,0.88)] text-[var(--text-tertiary)]",
          ].join(" ")}
        >
          {active ? "当前" : "进入"}
        </span>
      </span>
    </button>
  );
}
