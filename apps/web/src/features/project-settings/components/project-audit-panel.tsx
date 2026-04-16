"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import {
  buildProjectAuditQueryKey,
  formatProjectAuditTarget,
  formatProjectAuditTime,
  summarizeProjectAuditDetails,
} from "@/features/project-settings/components/project-audit-panel-support";
import { normalizeProjectAuditEventType } from "@/features/project-settings/components/project-settings-support";
import { getErrorMessage } from "@/lib/api/client";
import { listProjectAuditLogs } from "@/lib/api/observability";
import type { AuditLogView } from "@/lib/api/types";

type ProjectAuditPanelProps = {
  projectId: string;
  eventType: string | null;
  onEventTypeChange: (eventType: string | null) => void;
};

export function ProjectAuditPanel({
  projectId,
  eventType,
  onEventTypeChange,
}: ProjectAuditPanelProps) {
  const [draftFilterState, setDraftFilterState] = useState({
    sourceEventType: eventType,
    value: eventType ?? "",
  });
  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});
  const normalizedEventType = normalizeProjectAuditEventType(eventType);
  const draftEventType =
    draftFilterState.sourceEventType === eventType ? draftFilterState.value : (eventType ?? "");
  const query = useQuery({
    queryKey: buildProjectAuditQueryKey(projectId, normalizedEventType),
    queryFn: () => listProjectAuditLogs(projectId, normalizedEventType ?? undefined),
  });

  return (
    <SectionCard
      title="操作记录"
    >
      <div className="space-y-4">
        <AuditFilterBar
          draftEventType={draftEventType}
          onApply={() => onEventTypeChange(normalizeProjectAuditEventType(draftEventType))}
          onChange={(value) => setDraftFilterState({ sourceEventType: eventType, value })}
          onReset={() => {
            setDraftFilterState({ sourceEventType: eventType, value: "" });
            onEventTypeChange(null);
          }}
        />
        <AuditPanelBody
          error={query.error}
          eventType={normalizedEventType}
          isLoading={query.isLoading}
          items={query.data ?? []}
          onToggleItem={(itemId) =>
            setExpandedById((current) => ({ ...current, [itemId]: !current[itemId] }))
          }
          openById={expandedById}
        />
      </div>
    </SectionCard>
  );
}

function AuditFilterBar({
  draftEventType,
  onApply,
  onChange,
  onReset,
}: Readonly<{
  draftEventType: string;
  onApply: () => void;
  onChange: (value: string) => void;
  onReset: () => void;
}>) {
  const presetFilters = [
    { label: '项目更新', value: 'project.updated' },
    { label: '设置变更', value: 'project.setting.updated' },
    { label: '成员变动', value: 'project.member' },
  ];

  return (
    <form
      className="space-y-6 pb-6 border-b border-line-soft"
      onSubmit={(event) => {
        event.preventDefault();
        onApply();
      }}
    >
      <div className="flex flex-wrap gap-2">
        {presetFilters.map((preset) => (
          <button
            key={preset.value}
            className={`rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
              draftEventType === preset.value
                ? 'bg-accent-primary text-white shadow-sm'
                : 'bg-muted text-text-secondary hover:bg-surface-hover hover:shadow-sm'
            }`}
            onClick={() => onChange(preset.value)}
            type="button"
          >
            {preset.label}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="min-w-64 flex-1">
          <span className="label-text">操作类型过滤</span>
          <input
            className="ink-input"
            placeholder="如 project.updated / project.setting.updated"
            value={draftEventType}
            onChange={(event) => onChange(event.target.value)}
          />
        </label>
        <button className="ink-button-secondary" type="submit">
          应用过滤
        </button>
        <button className="ink-button-secondary" onClick={onReset} type="button">
          清空
        </button>
      </div>
    </form>
  );
}

function AuditPanelBody({
  error,
  eventType,
  isLoading,
  items,
  onToggleItem,
  openById,
}: Readonly<{
  error: unknown;
  eventType: string | null;
  isLoading: boolean;
  items: AuditLogView[];
  onToggleItem: (itemId: string) => void;
  openById: Record<string, boolean>;
}>) {
  if (isLoading) {
    return <div className="panel-muted px-4 py-5 text-sm text-text-secondary">正在加载项目审计日志...</div>;
  }
  if (error) {
    return (
      <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
        {getErrorMessage(error)}
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <EmptyState
        title="暂无项目审计日志"
        description={
          eventType
            ? `当前过滤条件 \`${eventType}\` 下没有记录。`
            : "暂无操作记录。"
        }
      />
    );
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <AuditLogCard
          key={item.id}
          isOpen={openById[item.id] ?? false}
          item={item}
          onToggle={() => onToggleItem(item.id)}
        />
      ))}
    </div>
  );
}

function AuditLogCard({
  isOpen,
  item,
  onToggle,
}: Readonly<{
  isOpen: boolean;
  item: AuditLogView;
  onToggle: () => void;
}>) {
  return (
    <article className="panel-muted space-y-3 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-text-primary">{item.event_type}</p>
            <span className="rounded-full bg-accent-primary/10 px-2 py-1 text-xs text-accent-primary">
              {formatProjectAuditTarget(item)}
            </span>
          </div>
          <p className="text-sm text-text-secondary">
            操作人: {item.actor_user_id ?? "系统"} · 详情: {summarizeProjectAuditDetails(item.details)}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="text-xs uppercase tracking-[0.16em] text-text-secondary">
            {formatProjectAuditTime(item.created_at)}
          </span>
          <button className="ink-button-secondary" onClick={onToggle} type="button">
            {isOpen ? "收起详情" : "展开详情"}
          </button>
        </div>
      </div>
      {isOpen ? <CodeBlock value={item.details} /> : null}
    </article>
  );
}
