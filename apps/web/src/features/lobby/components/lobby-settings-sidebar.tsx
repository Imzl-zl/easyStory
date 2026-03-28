"use client";

import { GuardedLink } from "@/components/ui/guarded-link";
import { SectionCard } from "@/components/ui/section-card";
import type { LobbySettingsTab } from "@/features/lobby/components/lobby-settings-support";

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
        description="管理模型连接、默认模型和长期规则。"
        title="AI 设置"
      >
        <div className="space-y-3">
          <LobbySettingsNavButton
            active={tab === "assistant"}
            description="默认连接、默认模型、长期规则"
            disabled={isPending}
            label="AI 助手"
            onClick={() => onSelectTab("assistant")}
          />
          <LobbySettingsNavButton
            active={tab === "credentials"}
            description="添加、验证、启用或切换模型连接"
            disabled={isPending}
            label="模型连接"
            onClick={() => onSelectTab("credentials")}
          />
        </div>
      </SectionCard>
      <div className="panel-muted space-y-2 px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        <p>管理个人默认设置。</p>
        <p>项目专属规则请前往“项目设置”。</p>
      </div>
    </aside>
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
      className="ink-tab w-full justify-start rounded-[20px] px-4 py-3 text-left"
      data-active={active}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <span className="flex flex-col items-start gap-1">
        <span className="text-sm font-medium text-[var(--text-primary)]">{label}</span>
        <span className="text-[12px] leading-5 text-[var(--text-secondary)]">{description}</span>
      </span>
    </button>
  );
}
