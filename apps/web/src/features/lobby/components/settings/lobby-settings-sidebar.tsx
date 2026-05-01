"use client";

import Link from "next/link";
import type { LobbySettingsTab } from "@/features/lobby/components/settings/lobby-settings-support";

const NAV_ITEMS: { label: string; tab: LobbySettingsTab; icon: React.ReactNode }[] = [
  {
    label: "模型连接",
    tab: "credentials",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
        <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
        <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
        <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
      </svg>
    ),
  },
  {
    label: "AI 助手",
    tab: "assistant",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" x2="12" y1="19" y2="22" />
      </svg>
    ),
  },
  {
    label: "Skills",
    tab: "skills",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      </svg>
    ),
  },
  {
    label: "MCP",
    tab: "mcp",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m18 16 4-4-4-4" />
        <path d="m6 8-4 4 4 4" />
        <path d="m14.5 4-5 16" />
      </svg>
    ),
  },
  {
    label: "Agents",
    tab: "agents",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 8V4H8" />
        <rect width="16" height="12" x="4" y="8" rx="2" />
        <path d="M2 14h2" />
        <path d="M20 14h2" />
        <path d="M15 13v2" />
        <path d="M9 13v2" />
      </svg>
    ),
  },
  {
    label: "Hooks",
    tab: "hooks",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" />
      </svg>
    ),
  },
];

type LobbySettingsSidebarProps = {
  isDirty: boolean;
  isPending: boolean;
  onNavigateAway: (onConfirm: () => void) => void;
  onSelectTab: (tab: LobbySettingsTab) => void;
  tab: LobbySettingsTab;
};

export function LobbySettingsSidebar({
  isPending,
  onSelectTab,
  tab,
}: Readonly<LobbySettingsSidebarProps>) {
  return (
    <aside className="flex flex-col h-full" style={{ background: "var(--bg-canvas)" }}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <Link href="/workspace/lobby" className="flex items-center gap-2.5 group">
          <span
            className="inline-flex items-center justify-center w-7 h-7 rounded-md text-[10px] font-bold tracking-wider"
            style={{
              background: "linear-gradient(135deg, var(--accent-primary), var(--accent-primary-dark))",
              color: "var(--text-on-accent)",
            }}
          >
            ES
          </span>
          <span className="text-[13px] font-medium tracking-tight" style={{ color: "var(--text-primary)" }}>
            easyStory
          </span>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.tab}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-all duration-150 group"
            disabled={isPending}
            onClick={() => onSelectTab(item.tab)}
            style={{
              background: tab === item.tab ? "var(--accent-primary-soft)" : "transparent",
            }}
            type="button"
          >
            <span
              className="flex items-center justify-center w-6 h-6 rounded-md transition-colors"
              style={{
                background: tab === item.tab ? "var(--accent-primary-soft)" : "transparent",
                color: tab === item.tab ? "var(--accent-primary)" : "var(--text-tertiary)",
              }}
            >
              {item.icon}
            </span>
            <span
              className="text-[12px] font-medium"
              style={{ color: tab === item.tab ? "var(--text-primary)" : "var(--text-secondary)" }}
            >
              {item.label}
            </span>
            {tab === item.tab && (
              <span className="ml-auto w-1 h-1 rounded-full" style={{ background: "var(--accent-primary)" }} />
            )}
          </button>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-4 py-3" style={{ borderTop: "1px solid var(--line-soft)" }}>
        <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
          个人默认设置
        </p>
      </div>
    </aside>
  );
}
