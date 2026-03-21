"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { getErrorMessage } from "@/lib/api/client";
import { downloadExportFile } from "@/lib/api/export";
import type { ExportView } from "@/lib/api/types";

type EngineExportPanelProps = {
  disabled: boolean;
  exports: ExportView[] | undefined;
  isPending: boolean;
  onCreate: () => void;
};

export function EngineExportPanel({
  disabled,
  exports,
  isPending,
  onCreate,
}: EngineExportPanelProps) {
  const [feedback, setFeedback] = useState<string | null>(null);
  const downloadMutation = useMutation({
    mutationFn: (item: ExportView) => downloadExportFile(item),
    onSuccess: (_, item) => setFeedback(`已开始下载 ${item.filename}。`),
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  return (
    <SectionCard
      title="Export Dialog"
      description="导出入口只挂在当前工作流，当前仅支持 txt 与 markdown。"
      action={
        <button className="ink-button" disabled={disabled || isPending} onClick={onCreate}>
          {isPending ? "导出中..." : "创建 txt + markdown 导出"}
        </button>
      }
    >
      {feedback ? (
        <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
          {feedback}
        </div>
      ) : null}
      {exports?.length ? (
        <div className="grid gap-3 md:grid-cols-2">
          {exports.map((item) => (
            <article key={item.id} className="panel-muted space-y-3 p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="space-y-1">
                  <h3 className="font-medium">{item.filename}</h3>
                  <p className="text-sm text-[var(--text-secondary)]">{item.format}</p>
                </div>
                <StatusBadge status="approved" label={item.format} />
              </div>
              <button
                className="ink-button-secondary w-full justify-center"
                disabled={downloadMutation.isPending}
                onClick={() => downloadMutation.mutate(item)}
              >
                {downloadMutation.isPending && downloadMutation.variables?.id === item.id
                  ? "下载中..."
                  : "下载导出文件"}
              </button>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="当前没有导出记录" description="先创建工作流导出，再从这里下载文件。" />
      )}
    </SectionCard>
  );
}
