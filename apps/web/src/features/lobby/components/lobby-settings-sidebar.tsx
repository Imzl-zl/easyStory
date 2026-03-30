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
        description="先完成长期规则、Skills 和模型连接；进阶能力按需要再添加。"
        title="AI 设置"
      >
        <div className="space-y-4">
          <LobbySettingsNavGroup title="先从这里开始">
            <LobbySettingsNavButton
              active={tab === "assistant"}
              description="长期规则、默认方式"
              disabled={isPending}
              label="AI 助手"
              onClick={() => onSelectTab("assistant")}
            />
            <LobbySettingsNavButton
              active={tab === "skills"}
              description="保存常用聊天方式"
              disabled={isPending}
              label="Skills"
              onClick={() => onSelectTab("skills")}
            />
            <LobbySettingsNavButton
              active={tab === "credentials"}
              description="选择默认连接和模型"
              disabled={isPending}
              label="模型连接"
              onClick={() => onSelectTab("credentials")}
            />
          </LobbySettingsNavGroup>
          <LobbySettingsNavGroup title="高级能力">
            <LobbySettingsNavButton
              active={tab === "agents"}
              description="进阶：固定助手角色"
              disabled={isPending}
              label="Agents"
              onClick={() => onSelectTab("agents")}
            />
            <LobbySettingsNavButton
              active={tab === "hooks"}
              description="进阶：自动动作"
              disabled={isPending}
              label="Hooks"
              onClick={() => onSelectTab("hooks")}
            />
            <LobbySettingsNavButton
              active={tab === "mcp"}
              description="进阶：外部工具连接"
              disabled={isPending}
              label="MCP"
              onClick={() => onSelectTab("mcp")}
            />
          </LobbySettingsNavGroup>
        </div>
      </SectionCard>
      <div className="panel-muted space-y-2 px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        <p>这里只管理你自己的默认设置。</p>
        <p>项目专属规则请前往“项目设置”。</p>
      </div>
    </aside>
  );
}

function LobbySettingsNavGroup({
  children,
  title,
}: Readonly<{
  children: React.ReactNode;
  title: string;
}>) {
  return (
    <div className="space-y-2">
      <p className="px-1 text-[11px] font-medium tracking-[0.08em] text-[var(--text-tertiary)] uppercase">
        {title}
      </p>
      <div className="space-y-3">{children}</div>
    </div>
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
