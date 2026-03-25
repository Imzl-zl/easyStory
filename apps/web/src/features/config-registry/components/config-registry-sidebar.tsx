"use client";

import { EmptyState } from "@/components/ui/empty-state";
import type { ConfigRegistrySummary, ConfigRegistryType } from "@/lib/api/types";

import {
  buildConfigRegistrySummaryRows,
  listConfigRegistryTabs,
  type ConfigRegistryMetaRow,
} from "./config-registry-support";

type ConfigRegistrySidebarProps = {
  activeItemId: string | null;
  errorMessage: string | null;
  isLoading: boolean;
  items: ConfigRegistrySummary[];
  onSelectItem: (itemId: string) => void;
  onSelectType: (type: ConfigRegistryType) => void;
  type: ConfigRegistryType;
};

export function ConfigRegistrySidebar({
  activeItemId,
  errorMessage,
  isLoading,
  items,
  onSelectItem,
  onSelectType,
  type,
}: Readonly<ConfigRegistrySidebarProps>) {
  const tabs = listConfigRegistryTabs();
  const activeTab = tabs.find((tab) => tab.key === type)!;

  return (
    <aside className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className="ink-tab"
            data-active={tab.key === type}
            onClick={() => onSelectType(tab.key)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="panel-muted space-y-2 p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">
          当前类型
        </p>
        <h3 className="font-serif text-lg font-semibold">{activeTab.label}</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          {activeTab.description}
        </p>
      </div>
      {errorMessage && items.length === 0 ? (
        <Banner tone="danger" message={errorMessage} />
      ) : null}
      {isLoading && items.length === 0 ? (
        <Banner tone="muted" message="正在加载配置列表..." />
      ) : null}
      {items.length === 0 && !isLoading && !errorMessage ? (
        <EmptyState
          title="暂无配置"
          description="当前配置仓还没有可展示的条目，或你没有对应的配置管理员访问权限。"
        />
      ) : (
        <div className="space-y-3">
          {errorMessage && items.length > 0 ? <Banner tone="danger" message={errorMessage} /> : null}
          {items.map((item) => (
            <SidebarCard
              key={item.id}
              isActive={item.id === activeItemId}
              item={item}
              rows={buildConfigRegistrySummaryRows(type, item).slice(0, 2)}
              onClick={() => onSelectItem(item.id)}
            />
          ))}
        </div>
      )}
    </aside>
  );
}

function SidebarCard({
  isActive,
  item,
  onClick,
  rows,
}: Readonly<{
  isActive: boolean;
  item: ConfigRegistrySummary;
  onClick: () => void;
  rows: ConfigRegistryMetaRow[];
}>) {
  return (
    <button
      className="w-full rounded-[24px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.58)] p-4 text-left transition data-[active=true]:border-[rgba(46,111,106,0.28)] data-[active=true]:bg-[rgba(46,111,106,0.08)]"
      data-active={isActive}
      onClick={onClick}
      type="button"
    >
      <div className="space-y-2">
        <div className="space-y-1">
          <p className="text-sm font-medium text-[var(--text-primary)]">{item.name}</p>
          <p className="text-xs text-[var(--text-secondary)]">{item.id}</p>
        </div>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          {item.description ?? "暂无描述。"}
        </p>
        <dl className="grid gap-2 text-xs text-[var(--text-secondary)]">
          {rows.map((row) => (
            <div key={row.label} className="flex justify-between gap-3">
              <dt>{row.label}</dt>
              <dd className="text-right text-[var(--text-primary)]">{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </button>
  );
}

function Banner({
  message,
  tone,
}: Readonly<{
  message: string;
  tone: "danger" | "muted";
}>) {
  if (tone === "danger") {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {message}
      </div>
    );
  }
  return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{message}</div>;
}
