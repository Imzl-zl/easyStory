"use client";

import { GuardedLink } from "@/components/ui/guarded-link";
import { SectionCard } from "@/components/ui/section-card";
import type { LobbySettingsTab } from "@/features/lobby/components/settings/lobby-settings-support";

const PRIMARY_NAV_ITEMS = [
  { label: "AI 助手", tab: "assistant" },
  { label: "Skills", tab: "skills" },
  { label: "模型连接", tab: "credentials" },
] as const;

const ADVANCED_NAV_ITEMS = [
  { label: "Agents", tab: "agents" },
  { label: "Hooks", tab: "hooks" },
  { label: "MCP", tab: "mcp" },
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
        bodyClassName="space-y-4"
        className="bg-glass shadow-glass backdrop-blur-lg"
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
        title="AI 设置"
      >
        <LobbySettingsNavGroup
          items={PRIMARY_NAV_ITEMS}
          isPending={isPending}
          onSelectTab={onSelectTab}
          tab={tab}
          title="主路径"
        />
        <LobbySettingsNavGroup
          items={ADVANCED_NAV_ITEMS}
          isPending={isPending}
          onSelectTab={onSelectTab}
          tab={tab}
          title="高级能力"
        />
      </SectionCard>
      <div className="panel-muted space-y-2 px-4 py-4 text-sm leading-6 text-text-secondary">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-text-tertiary uppercase">作用域</p>
        <p>这里只管理你自己的默认设置。</p>
        <p>项目专属规则请前往“项目设置”。</p>
      </div>
    </aside>
  );
}

function LobbySettingsNavGroup({
  isPending,
  items,
  onSelectTab,
  tab,
  title,
}: Readonly<{
  isPending: boolean;
  items: readonly { label: string; tab: LobbySettingsTab }[];
  onSelectTab: (tab: LobbySettingsTab) => void;
  tab: LobbySettingsTab;
  title: string;
}>) {
  return (
    <section className="space-y-3">
      <div className="px-1">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-text-tertiary uppercase">{title}</p>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <LobbySettingsNavButton
            active={tab === item.tab}
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
  disabled,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  disabled: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={[
        "w-full rounded-2xl px-4 py-3.5 text-left transition-all duration-fast",
        active
          ? "bg-accent-soft shadow-sm"
          : "bg-surface shadow-xs hover:bg-surface-hover hover:shadow-sm",
      ].join(" ")}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <span className="flex items-start justify-between gap-3">
        <span className="flex flex-col items-start">
          <span className="text-sm font-semibold text-text-primary">{label}</span>
        </span>
        <span
          className={[
            "rounded-pill px-2.5 py-1 text-[11px] font-semibold tracking-[0.12em] uppercase",
            active
              ? "bg-accent-primary-muted text-accent-primary"
              : "bg-muted text-text-tertiary",
          ].join(" ")}
        >
          {active ? "当前" : "进入"}
        </span>
      </span>
    </button>
  );
}
