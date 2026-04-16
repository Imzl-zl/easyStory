"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { DialogShell } from "@/components/ui/dialog-shell";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildExportPrecheck,
  DEFAULT_EXPORT_FORMATS,
  formatExportFileSize,
  formatExportTimestamp,
  resolveExportCreateDisabledReason,
  toggleExportFormat,
} from "@/features/engine/components/engine-export-support";
import { getErrorMessage } from "@/lib/api/client";
import { createWorkflowExports, downloadExportFile, listProjectExports } from "@/lib/api/export";
import { listChapterTasks } from "@/lib/api/workflow";
import type { ExportView } from "@/lib/api/types";

type EngineExportPanelProps = {
  onClose: () => void;
  projectId: string;
  workflowId: string;
};

export function EngineExportPanel({
  onClose,
  projectId,
  workflowId,
}: EngineExportPanelProps) {
  const queryClient = useQueryClient();
  const [selectedFormats, setSelectedFormats] = useState<string[]>([...DEFAULT_EXPORT_FORMATS]);
  const tasksQuery = useQuery({
    queryKey: ["workflow-tasks", workflowId],
    queryFn: () => listChapterTasks(workflowId),
    enabled: Boolean(workflowId),
  });
  const exportsQuery = useQuery({
    queryKey: ["project-exports", projectId],
    queryFn: () => listProjectExports(projectId),
    enabled: Boolean(projectId),
  });
  const downloadMutation = useMutation({
    mutationFn: (item: ExportView) => downloadExportFile(item),
    onSuccess: (_, item) =>
      showAppNotice({
        content: `已开始下载 ${item.filename}。`,
        title: "导出成稿",
        tone: "success",
      }),
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "导出成稿",
        tone: "danger",
      }),
  });
  const createMutation = useMutation({
    mutationFn: () => createWorkflowExports(workflowId, { formats: selectedFormats }),
    onSuccess: (items) => {
      showAppNotice({
        content: `已创建 ${items.length} 份导出文件。`,
        title: "导出成稿",
        tone: "success",
      });
      queryClient.invalidateQueries({ queryKey: ["project-exports", projectId] });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "导出成稿",
        tone: "danger",
      }),
  });
  const tasks = tasksQuery.data ?? [];
  const precheck = buildExportPrecheck(tasks);
  const createDisabledReason = resolveExportCreateDisabledReason({
    blockingCount: precheck.blockingItems.length,
    hasWorkflow: Boolean(workflowId),
    selectedFormatsCount: selectedFormats.length,
    taskCount: tasks.length,
  });
  const exports = exportsQuery.data;

  return (
    <DialogShell
      title="导出成稿"
      onClose={onClose}
    >
      <div className="grid gap-4 xl:grid-cols-[0.94fr_1.06fr]">
        <section className="panel-muted space-y-4 p-5">
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">导出前预检</h3>
          </div>
          {!workflowId ? (
            <EmptyState title="尚未载入工作流" description="请先载入工作流，再发起导出。" />
          ) : (
            <>
              <FormatSelection
                selectedFormats={selectedFormats}
                onToggle={(value) => setSelectedFormats((current) => toggleExportFormat(current, value))}
              />
              {tasksQuery.isPending ? <p className="text-sm text-text-secondary">正在检查章节状态...</p> : null}
              {tasksQuery.error ? (
                <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
                  {getErrorMessage(tasksQuery.error)}
                </div>
              ) : null}
              {!tasksQuery.isPending && !tasksQuery.error ? (
                <div className="space-y-3">
                  <PrecheckGroup items={precheck.blockingItems} tone="failed" title="阻断项" />
                  <PrecheckGroup items={precheck.warningItems} tone="warning" title="警示项" />
                  <PrecheckGroup items={precheck.infoItems} tone="draft" title="导出备注" />
                  {tasks.length === 0 ? (
                    <EmptyState title="当前没有章节计划" description="工作流尚未生成章节任务。" />
                  ) : precheck.blockingItems.length === 0 ? (
                    <div className="callout-success px-4 py-3 text-sm text-accent-success">
                      当前章节任务已满足导出条件。
                      {precheck.warningItems.length > 0 ? "存在 warning，导出前请确认这些章节仍可接受。" : ""}
                    </div>
                  ) : null}
                </div>
              ) : null}
              <div className="flex flex-wrap gap-3">
                <button
                  className="ink-button"
                  disabled={Boolean(createDisabledReason) || createMutation.isPending}
                  onClick={() => createMutation.mutate()}
                  type="button"
                >
                  {createMutation.isPending ? "导出中..." : "创建导出文件"}
                </button>
                <button className="ink-button-secondary" onClick={onClose} type="button">
                  关闭
                </button>
              </div>
              {createDisabledReason ? (
                <p className="text-sm leading-6 text-accent-warning">{createDisabledReason}</p>
              ) : null}
            </>
          )}
        </section>
        <section className="panel-muted space-y-4 p-5">
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">项目导出历史</h3>
            <p className="text-sm leading-6 text-text-secondary">
              按项目查看导出记录。
            </p>
          </div>
          {exportsQuery.isPending ? <p className="text-sm text-text-secondary">正在加载导出历史...</p> : null}
          {exportsQuery.error ? (
            <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
              {getErrorMessage(exportsQuery.error)}
            </div>
          ) : null}
          {exports?.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {exports.map((item) => (
                <article key={item.id} className="rounded-2xl bg-muted shadow-sm p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <h4 className="break-all text-sm font-medium text-text-primary">{item.filename}</h4>
                      <p className="text-xs uppercase tracking-[0.14em] text-text-secondary">
                        {formatExportTimestamp(item.created_at)}
                      </p>
                    </div>
                    <StatusBadge status="approved" label={item.format.toUpperCase()} />
                  </div>
                  <div className="mt-4 grid gap-2 text-sm text-text-secondary">
                    <p>体积：{formatExportFileSize(item.file_size)}</p>
                    <p>格式：{item.format}</p>
                  </div>
                  <button
                    className="ink-button-secondary mt-4 w-full justify-center"
                    disabled={downloadMutation.isPending}
                    onClick={() => downloadMutation.mutate(item)}
                    type="button"
                  >
                    {downloadMutation.isPending && downloadMutation.variables?.id === item.id ? "下载中..." : "下载导出文件"}
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="尚未付梓" description="完成导出后，可以在这里下载文件。" />
          )}
        </section>
      </div>
    </DialogShell>
  );
}

function FormatSelection({
  selectedFormats,
  onToggle,
}: Readonly<{
  selectedFormats: string[];
  onToggle: (value: string) => void;
}>) {
  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h4 className="text-sm font-medium text-text-primary">导出格式</h4>
        <p className="text-sm leading-6 text-text-secondary">至少选择一种格式。当前能力只开放 txt 与 markdown。</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {DEFAULT_EXPORT_FORMATS.map((format) => {
          const selected = selectedFormats.includes(format);
          return (
            <button
              aria-pressed={selected}
              className="ink-tab"
              data-active={selected}
              key={format}
              onClick={() => onToggle(format)}
              type="button"
            >
              {format.toUpperCase()}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function PrecheckGroup({
  items,
  title,
  tone,
}: Readonly<{
  items: { chapterNumber: number; detail: string; title: string }[];
  title: string;
  tone: "draft" | "failed" | "warning";
}>) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <StatusBadge status={tone} label={title} />
        <span className="text-sm text-text-secondary">{items.length} 项</span>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <article
            className="rounded-2xl bg-glass shadow-glass px-4 py-3"
            key={`${title}-${item.chapterNumber}-${item.title}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status="outline" label={`第 ${item.chapterNumber} 章`} />
              <span className="text-sm font-medium text-text-primary">{item.title}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-text-secondary">{item.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
