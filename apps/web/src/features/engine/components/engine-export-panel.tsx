"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { DialogShell } from "@/components/ui/dialog-shell";
import { EmptyState } from "@/components/ui/empty-state";
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
      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <div className="space-y-3">
          <div className="rounded p-4" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
            <h3 className="text-[12px] font-medium mb-3" style={{ color: "var(--text-tertiary)" }}>导出前预检</h3>
            {!workflowId ? (
              <EmptyState title="尚未载入工作流" description="请先载入工作流，再发起导出。" />
            ) : (
              <div className="space-y-3">
                <FormatSelection
                  selectedFormats={selectedFormats}
                  onToggle={(value) => setSelectedFormats((current) => toggleExportFormat(current, value))}
                />
                {tasksQuery.isPending ? <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>正在检查章节状态...</p> : null}
                {tasksQuery.error ? (
                  <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
                    {getErrorMessage(tasksQuery.error)}
                  </div>
                ) : null}
                {!tasksQuery.isPending && !tasksQuery.error ? (
                  <div className="space-y-2">
                    <PrecheckGroup items={precheck.blockingItems} tone="failed" title="阻断项" />
                    <PrecheckGroup items={precheck.warningItems} tone="warning" title="警示项" />
                    <PrecheckGroup items={precheck.infoItems} tone="draft" title="导出备注" />
                    {tasks.length === 0 ? (
                      <EmptyState title="当前没有章节计划" description="工作流尚未生成章节任务。" />
                    ) : precheck.blockingItems.length === 0 ? (
                      <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-success-soft)", color: "var(--accent-success)" }}>
                        当前章节任务已满足导出条件。
                        {precheck.warningItems.length > 0 ? "存在 warning，导出前请确认这些章节仍可接受。" : ""}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <button
                    className="px-4 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40"
                    style={{ background: "var(--accent-primary)", color: "var(--bg-canvas)" }}
                    disabled={Boolean(createDisabledReason) || createMutation.isPending}
                    onClick={() => createMutation.mutate()}
                    type="button"
                  >
                    {createMutation.isPending ? "导出中..." : "创建导出文件"}
                  </button>
                  <button
                    className="px-4 py-2 rounded text-[12px] font-medium transition-colors"
                    style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
                    onClick={onClose}
                    type="button"
                  >
                    关闭
                  </button>
                </div>
                {createDisabledReason ? (
                  <p className="text-[11px]" style={{ color: "var(--accent-warning)" }}>{createDisabledReason}</p>
                ) : null}
              </div>
            )}
          </div>
        </div>

        <div className="rounded p-4" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
          <h3 className="text-[12px] font-medium mb-3" style={{ color: "var(--text-tertiary)" }}>项目导出历史</h3>
          {exportsQuery.isPending ? <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>正在加载导出历史...</p> : null}
          {exportsQuery.error ? (
            <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              {getErrorMessage(exportsQuery.error)}
            </div>
          ) : null}
          {exports?.length ? (
            <div className="grid gap-2 grid-cols-2">
              {exports.map((item) => (
                <article key={item.id} className="rounded p-3" style={{ background: "var(--bg-muted)" }}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-0.5 min-w-0">
                      <h4 className="break-all text-[12px] font-medium truncate" style={{ color: "var(--text-primary)" }}>{item.filename}</h4>
                      <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                        {formatExportTimestamp(item.created_at)}
                      </p>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded flex-shrink-0" style={{ background: "var(--accent-success-soft)", color: "var(--accent-success)" }}>
                      {item.format.toUpperCase()}
                    </span>
                  </div>
                  <div className="mt-2 space-y-0.5">
                    <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>体积：{formatExportFileSize(item.file_size)}</p>
                    <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>格式：{item.format}</p>
                  </div>
                  <button
                    className="w-full mt-2 px-3 py-1.5 rounded text-[11px] font-medium transition-colors"
                    style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
                    disabled={downloadMutation.isPending}
                    onClick={() => downloadMutation.mutate(item)}
                    type="button"
                  >
                    {downloadMutation.isPending && downloadMutation.variables?.id === item.id ? "下载中..." : "下载"}
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="尚未付梓" description="完成导出后，可以在这里下载文件。" />
          )}
        </div>
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
    <div className="space-y-2">
      <p className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>导出格式</p>
      <div className="flex flex-wrap gap-1.5">
        {DEFAULT_EXPORT_FORMATS.map((format) => {
          const selected = selectedFormats.includes(format);
          return (
            <button
              aria-pressed={selected}
              className="px-3 py-1.5 rounded text-[11px] font-medium transition-all"
              style={{
                background: selected ? "var(--accent-primary)" : "var(--line-soft)",
                color: selected ? "var(--bg-canvas)" : "var(--text-secondary)",
              }}
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
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <StatusPill tone={tone} label={title} />
        <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{items.length} 项</span>
      </div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div
            className="rounded p-2.5"
            style={{ background: "var(--bg-muted)" }}
            key={`${title}-${item.chapterNumber}-${item.title}`}
          >
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}>第 {item.chapterNumber} 章</span>
              <span className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>{item.title}</span>
            </div>
            <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>{item.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusPill({ tone, label }: { tone: string; label: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "var(--accent-success-soft)", text: "var(--accent-success)" },
    failed: { bg: "var(--accent-danger-soft)", text: "var(--accent-danger)" },
    warning: { bg: "var(--accent-warning-soft)", text: "var(--accent-warning)" },
    active: { bg: "var(--accent-primary-soft)", text: "var(--accent-primary)" },
    outline: { bg: "var(--line-soft)", text: "var(--text-secondary)" },
    draft: { bg: "var(--line-soft)", text: "var(--text-tertiary)" },
  };
  const c = colors[tone] || colors.outline;
  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-medium"
      style={{ background: c.bg, color: c.text }}
    >
      {label}
    </span>
  );
}
