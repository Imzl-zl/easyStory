"use client";

import { AppSelect } from "@/components/ui/app-select";
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
      <div className="flex flex-wrap gap-2.5">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className="ink-tab h-9 px-4 text-[13px]"
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
          <p className="text-xs tracking-[0.16em] text-accent-primary">系统分类</p>
          <h3 className="font-serif text-lg font-semibold">{activeTab.label}</h3>
          <p className="text-sm leading-6 text-text-secondary">{activeTab.description}</p>
        </div>

        <label className="block space-y-2">
          <span className="label-text">搜索</span>
          <input
            autoComplete="off"
            className="ink-input"
            name="config-registry-query"
            placeholder="搜索名称或编号…"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>

        <label className="block space-y-2">
          <span className="label-text">排序</span>
          <AppSelect
            options={[
              { label: "名称 A-Z", value: "name_asc" },
              { label: "名称 Z-A", value: "name_desc" },
            ]}
            value={sort}
            onChange={(value) => onSortChange(value as ConfigRegistrySortValue)}
          />
        </label>

        {supportsConfigRegistryTagFilter(type) ? (
          <div className="space-y-2">
            <span className="label-text">标签过滤</span>
            {availableTags.length > 0 ? (
              <div className="flex flex-wrap gap-2.5">
                {availableTags.map((tag) => (
                  <button
                    key={tag}
                    className="ink-tab h-9 px-4 text-[13px]"
                    data-active={tags.includes(tag)}
                    type="button"
                    onClick={() => onTagToggle(tag)}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-secondary">这一类暂时没有可筛选标签。</p>
            )}
          </div>
        ) : null}

        {supportsConfigRegistryStatusFilter(type) ? (
          <div className="space-y-2">
            <span className="label-text">状态过滤</span>
            <div className="flex flex-wrap gap-2.5">
              {[
                { label: "全部", value: "all" },
                { label: "已启用", value: "enabled" },
                { label: "已停用", value: "disabled" },
              ].map((option) => (
                <button
                  key={option.value}
                  className="ink-tab h-9 px-4 text-[13px]"
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
      {isLoading && items.length === 0 ? <Banner message="正在加载内容…" tone="muted" /> : null}
      {items.length === 0 && !isLoading && !errorMessage ? (
        <EmptyState title="暂时没有内容" description="当前筛选条件下没有匹配结果，或者你还没有查看权限。" />
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
      className="w-full rounded-3xl bg-muted shadow-sm p-4 text-left transition data-[active=true]:border-accent-primary/25 data-[active=true]:bg-accent-soft"
      data-active={isActive}
      data-enabled={enabled}
      type="button"
      onClick={onClick}
    >
      <div className="space-y-2">
        <div className="space-y-1">
          <p className="text-sm font-medium text-text-primary">{item.name}</p>
          <p className="text-xs text-text-secondary">{item.id}</p>
        </div>
        <p className="text-sm leading-6 text-text-secondary">{item.description ?? "暂无描述。"}</p>
        <dl className="grid gap-2">
          {rows.map((row) => (
            <div key={row.label} className="grid grid-cols-[68px_1fr] gap-2 text-xs text-text-secondary">
              <dt>{row.label}</dt>
              <dd className="min-w-0 break-words text-text-primary">{row.value}</dd>
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
      <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
        {message}
      </div>
    );
  }
  return <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{message}</div>;
}
