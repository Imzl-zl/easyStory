"use client";

import { EmptyState } from "@/components/ui/empty-state";
import type { ConfigRegistrySummary, ConfigRegistryType } from "@/lib/api/types";

import type {
  ConfigRegistrySortValue,
  ConfigRegistryStatusValue,
} from "./config-registry-state-support";
import {
  supportsConfigRegistryStatusFilter,
  supportsConfigRegistryTagFilter,
} from "./config-registry-state-support";
import {
  buildConfigRegistrySummaryRows,
  listConfigRegistryTabs,
  type ConfigRegistryMetaRow,
} from "./config-registry-support";

type ConfigRegistrySidebarProps = {
  activeItemId: string | null;
  availableTags: string[];
  errorMessage: string | null;
  isLoading: boolean;
  items: ConfigRegistrySummary[];
  query: string;
  sort: ConfigRegistrySortValue;
  status: ConfigRegistryStatusValue;
  tags: string[];
  type: ConfigRegistryType;
  onQueryChange: (value: string) => void;
  onSelectItem: (itemId: string) => void;
  onSelectType: (type: ConfigRegistryType) => void;
  onSortChange: (value: ConfigRegistrySortValue) => void;
  onStatusChange: (value: ConfigRegistryStatusValue) => void;
  onTagToggle: (tag: string) => void;
};

export function ConfigRegistrySidebar({
  activeItemId,
  availableTags,
  errorMessage,
  isLoading,
  items,
  onQueryChange,
  onSelectItem,
  onSelectType,
  onSortChange,
  onStatusChange,
  onTagToggle,
  query,
  sort,
  status,
  tags,
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
            type="button"
            onClick={() => onSelectType(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="panel-muted space-y-4 p-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">当前类型</p>
          <h3 className="font-serif text-lg font-semibold">{activeTab.label}</h3>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">{activeTab.description}</p>
        </div>

        <label className="block space-y-2">
          <span className="label-text">搜索</span>
          <input
            autoComplete="off"
            className="ink-input"
            name="config-registry-query"
            placeholder="搜索配置名称、ID…"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>

        <label className="block space-y-2">
          <span className="label-text">排序</span>
          <select
            autoComplete="off"
            className="ink-select"
            name="config-registry-sort"
            value={sort}
            onChange={(event) => onSortChange(event.target.value as ConfigRegistrySortValue)}
          >
            <option value="name_asc">名称 A-Z</option>
            <option value="name_desc">名称 Z-A</option>
          </select>
        </label>

        {supportsConfigRegistryTagFilter(type) ? (
          <div className="space-y-2">
            <span className="label-text">标签过滤</span>
            {availableTags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {availableTags.map((tag) => (
                  <button
                    key={tag}
                    className="ink-tab"
                    data-active={tags.includes(tag)}
                    type="button"
                    onClick={() => onTagToggle(tag)}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">当前类型暂无标签可筛选。</p>
            )}
          </div>
        ) : null}

        {supportsConfigRegistryStatusFilter(type) ? (
          <div className="space-y-2">
            <span className="label-text">状态过滤</span>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "全部", value: "all" },
                { label: "已启用", value: "enabled" },
                { label: "已停用", value: "disabled" },
              ].map((option) => (
                <button
                  key={option.value}
                  className="ink-tab"
                  data-active={status === option.value}
                  type="button"
                  onClick={() => onStatusChange(option.value as ConfigRegistryStatusValue)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {errorMessage && items.length === 0 ? <Banner message={errorMessage} tone="danger" /> : null}
      {isLoading && items.length === 0 ? <Banner message="正在加载配置列表…" tone="muted" /> : null}
      {items.length === 0 && !isLoading && !errorMessage ? (
        <EmptyState title="暂无配置" description="当前过滤条件下没有匹配项，或账号无访问权限。" />
      ) : (
        <div className="space-y-3">
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
  const enabled = "enabled" in item ? String(item.enabled) : undefined;
  return (
    <button
      className="w-full rounded-[24px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.58)] p-4 text-left transition data-[active=true]:border-[rgba(46,111,106,0.28)] data-[active=true]:bg-[rgba(46,111,106,0.08)]"
      data-active={isActive}
      data-enabled={enabled}
      type="button"
      onClick={onClick}
    >
      <div className="space-y-2">
        <div className="space-y-1">
          <p className="text-sm font-medium text-[var(--text-primary)]">{item.name}</p>
          <p className="text-xs text-[var(--text-secondary)]">{item.id}</p>
        </div>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">{item.description ?? "暂无描述。"}</p>
        <dl className="grid gap-2">
          {rows.map((row) => (
            <div key={row.label} className="grid grid-cols-[68px_1fr] gap-2 text-xs text-[var(--text-secondary)]">
              <dt>{row.label}</dt>
              <dd className="min-w-0 break-words text-[var(--text-primary)]">{row.value}</dd>
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
