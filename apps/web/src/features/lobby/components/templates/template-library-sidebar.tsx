"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { RequestStateCard } from "@/features/lobby/components/common/request-state";
import type { TemplateLibraryModel } from "@/features/lobby/components/templates/template-library-model";
import type { TemplateVisibilityFilter } from "@/features/lobby/components/templates/template-library-support";
import { getErrorMessage } from "@/lib/api/client";
import type { TemplateSummary } from "@/lib/api/types";

export function TemplateLibrarySidebar({ model }: { model: TemplateLibraryModel }) {
  return (
    <aside className="panel-shell flex min-h-0 flex-col gap-4 p-5">
      <SidebarHeader onStartCreate={model.startCreate} />
      <SidebarFilters model={model} />
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        <SidebarBody model={model} />
      </div>
    </aside>
  );
}

function SidebarHeader({ onStartCreate }: { onStartCreate: () => void }) {
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.24em] text-[var(--accent-ink)]">模板库</p>
        <h2 className="font-serif text-2xl font-semibold">模板列表</h2>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          管理内置模板和自定义模板。
        </p>
      </div>
      <button className="ink-button w-full justify-center" onClick={onStartCreate} type="button">
        创建模板
      </button>
    </div>
  );
}

function SidebarFilters({ model }: { model: TemplateLibraryModel }) {
  return (
    <div className="space-y-3">
      <label className="block">
        <span className="label-text">搜索模板</span>
        <input
          className="ink-input"
          placeholder="按名称、描述、题材过滤"
          value={model.searchText}
          onChange={(event) => model.setSearchText(event.target.value)}
        />
      </label>
      <VisibilityTabs visibility={model.visibility} onChange={model.setVisibility} />
      {model.genres.length > 0 ? (
        <GenreTabs
          genreFilter={model.genreFilter}
          genres={model.genres}
          onChange={model.setGenreFilter}
        />
      ) : null}
    </div>
  );
}

function VisibilityTabs({
  visibility,
  onChange,
}: {
  visibility: TemplateVisibilityFilter;
  onChange: (value: TemplateVisibilityFilter) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {[
        ["all", "全部"],
        ["builtin", "内置"],
        ["custom", "自定义"],
      ].map(([value, label]) => (
        <button
          key={value}
          className="ink-tab"
          data-active={visibility === value}
          onClick={() => onChange(value as TemplateVisibilityFilter)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function GenreTabs({
  genres,
  genreFilter,
  onChange,
}: {
  genres: string[];
  genreFilter: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button className="ink-tab" data-active={genreFilter === "all"} onClick={() => onChange("all")} type="button">
        全题材
      </button>
      {genres.map((genre) => (
        <button
          key={genre}
          className="ink-tab"
          data-active={genreFilter === genre}
          onClick={() => onChange(genre)}
          type="button"
        >
          {genre}
        </button>
      ))}
    </div>
  );
}

function SidebarBody({ model }: { model: TemplateLibraryModel }) {
  if (model.templatesQuery.isLoading) {
    return <p className="text-sm text-[var(--text-secondary)]">正在读取模板列表…</p>;
  }
  if (model.templatesQuery.error) {
    return (
      <RequestStateCard
        title="模板列表加载失败"
        message={getErrorMessage(model.templatesQuery.error)}
        actions={
          <button className="ink-button-secondary" onClick={() => void model.templatesQuery.refetch()} type="button">
            重试
          </button>
        }
      />
    );
  }
  if (model.filteredTemplates.length === 0) {
    return (
      <EmptyState
        title="暂无模板"
        description="创建模板，或使用内置模板。"
      />
    );
  }
  return (
    <div className="space-y-3">
      {model.filteredTemplates.map((template) => (
        <TemplateListCard
          key={template.id}
          activeTemplateId={model.activeTemplateId}
          template={template}
          onSelect={model.selectTemplate}
        />
      ))}
    </div>
  );
}

function TemplateListCard({
  template,
  activeTemplateId,
  onSelect,
}: {
  template: TemplateSummary;
  activeTemplateId: string | null;
  onSelect: (templateId: string) => void;
}) {
  return (
    <button className="panel-muted w-full space-y-3 p-4 text-left" data-active={template.id === activeTemplateId} onClick={() => onSelect(template.id)} type="button">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-serif text-lg font-semibold">{template.name}</p>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">{template.description ?? "暂无说明。"}</p>
        </div>
        <StatusBadge
          status={template.is_builtin ? "approved" : "draft"}
          label={template.is_builtin ? "内置" : "自定义"}
        />
      </div>
      <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">
        <span>{template.genre ?? "未设题材"}</span>
        <span>{template.node_count} 步</span>
      </div>
    </button>
  );
}
